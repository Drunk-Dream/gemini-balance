import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.decorators import log_function_calls
from app.core.logging import setup_debug_logger
from pydantic import BaseModel, Field

# 为 RedisKeyManager 创建一个专用的日志记录器
key_manager_logger = setup_debug_logger("key_manager")


class RedisHealthCheckResult(BaseModel):
    is_healthy: bool
    error_code: int = 0
    message: str = ""
    added_keys: List[str] = Field(default_factory=list)
    missing_keys: List[str] = Field(default_factory=list)
    extra_keys_in_redis: List[str] = Field(default_factory=list)
    missing_states: List[str] = Field(default_factory=list)
    extra_states_in_redis: List[str] = Field(default_factory=list)


class KeyState(BaseModel):
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    usage_today: Dict[str, int] = Field(default_factory=dict)
    last_usage_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )

    def to_redis_hash(self) -> Dict[str, str]:
        """将 KeyState 转换为 Redis Hash 存储的字典。"""
        return {
            "cool_down_until": str(self.cool_down_until),
            "request_fail_count": str(self.request_fail_count),
            "cool_down_entry_count": str(self.cool_down_entry_count),
            "current_cool_down_seconds": str(self.current_cool_down_seconds),
            "usage_today": json.dumps(self.usage_today),
            "last_usage_date": self.last_usage_date,
        }

    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> "KeyState":
        """从 Redis Hash 字典创建 KeyState 实例。"""
        return cls(
            cool_down_until=float(data.get("cool_down_until", 0.0)),
            request_fail_count=int(data.get("request_fail_count", 0)),
            cool_down_entry_count=int(data.get("cool_down_entry_count", 0)),
            current_cool_down_seconds=int(
                data.get(
                    "current_cool_down_seconds", settings.API_KEY_COOL_DOWN_SECONDS
                )
            ),
            usage_today=json.loads(data.get("usage_today", "{}")),
            last_usage_date=data.get(
                "last_usage_date", datetime.now().strftime("%Y-%m-%d")
            ),
        )


class KeyStatusResponse(BaseModel):
    key_identifier: str
    status: str
    cool_down_seconds_remaining: float
    daily_usage: Dict[str, int]
    failure_count: int
    cool_down_entry_count: int
    current_cool_down_seconds: int


class RedisKeyManager:
    def __init__(
        self,
        redis_client: redis.Redis,
        api_keys: List[str],
    ):
        if not api_keys:
            raise ValueError("API key list cannot be empty.")
        self._redis = redis_client
        # 创建从密钥标识符到原始密钥的映射
        self._key_map = {self._get_key_identifier(key): key for key in api_keys}
        # 将原始 API 密钥转换为哈希标识符
        self._api_keys = list(self._key_map.keys())
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._lock = asyncio.Lock()  # 用于保护 Redis 操作的本地锁
        self._background_task: Optional[asyncio.Task] = None
        self._wakeup_event = asyncio.Event()

        self.AVAILABLE_KEYS_KEY = "key_manager:available_keys"
        self.COOLED_DOWN_KEYS_KEY = "key_manager:cooled_down_keys"
        self.KEY_STATE_PREFIX = "key_manager:state:"
        self.ALL_KEYS_SET_KEY = "key_manager:all_keys"  # 新增的 Redis 键

    async def _get_key_state(self, key_identifier: str) -> KeyState:
        """从 Redis 获取密钥状态，如果不存在则初始化。"""
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
        if state_data:
            # 将 bytes 转换为 str
            decoded_data = {k.decode(): v.decode() for k, v in state_data.items()}
            return KeyState.from_redis_hash(decoded_data)
        else:
            # 初始化并保存到 Redis
            initial_state = KeyState(
                current_cool_down_seconds=self._initial_cool_down_seconds
            )
            await self._redis.hset(  # type: ignore
                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                mapping=initial_state.to_redis_hash(),
            )
            return initial_state

    async def _save_key_state(self, key_identifier: str, state: KeyState):
        """将密钥状态保存到 Redis。"""
        await self._redis.hset(  # type: ignore
            f"{self.KEY_STATE_PREFIX}{key_identifier}", mapping=state.to_redis_hash()
        )

    async def _reset_daily_usage_if_needed(self, key_state: KeyState) -> bool:
        """
        如果密钥的最后使用日期不是今天，则重置每日用量。
        返回 True 如果用量被重置，否则返回 False。
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        if key_state.last_usage_date != today_str:
            key_state.usage_today = {}
            key_state.last_usage_date = today_str
            return True
        return False

    async def _check_redis_health_internal(self) -> RedisHealthCheckResult:
        """
        执行 Redis 数据库的健康检查（内部方法，不加锁）。
        检查项包括：
        1. 配置中的 API 密钥与 Redis 中 ALL_KEYS_SET_KEY 的一致性。
        2. ALL_KEYS_SET_KEY 中的密钥与 AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY 的一致性。
        3. ALL_KEYS_SET_KEY 中的每个密钥是否都有对应的 KeyState。
        """
        config_key_identifiers = set(self._api_keys)  # 使用哈希标识符

        # 检查 1: 配置中的 API 密钥与 ALL_KEYS_SET_KEY 的一致性
        key_manager_logger.info(
            "Health Check 1: Comparing config key identifiers " "with ALL_KEYS_SET_KEY."
        )
        redis_all_key_identifiers_bytes = await self._redis.smembers(self.ALL_KEYS_SET_KEY)  # type: ignore
        redis_all_key_identifiers = {
            key.decode() for key in redis_all_key_identifiers_bytes
        }

        added_in_config = list(config_key_identifiers - redis_all_key_identifiers)
        missing_in_config = list(redis_all_key_identifiers - config_key_identifiers)

        if added_in_config or missing_in_config:
            key_manager_logger.warning(
                "Health Check 1 Failed:"
                " Mismatch between config key identifiers and ALL_KEYS_SET_KEY."
            )
            if added_in_config:
                key_manager_logger.warning(
                    f"Key identifiers to add from config: {added_in_config}"
                )
            if missing_in_config:
                key_manager_logger.warning(
                    f"Key identifiers to remove from Redis: {missing_in_config}"
                )
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=1,
                message="Config key identifiers and ALL_KEYS_SET_KEY mismatch.",
                added_keys=added_in_config,
                missing_keys=missing_in_config,
            )
        key_manager_logger.info(
            "Health Check 1 Passed:"
            " Config key identifiers and ALL_KEYS_SET_KEY are consistent."
        )

        # 检查 2: ALL_KEYS_SET_KEY 中的密钥与 AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY 的一致性
        key_manager_logger.info(
            "Health Check 2: Comparing ALL_KEYS_SET_KEY "
            "with AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY."
        )
        available_key_identifiers_bytes = await self._redis.lrange(self.AVAILABLE_KEYS_KEY, 0, -1)  # type: ignore
        available_key_identifiers = {
            key.decode() for key in available_key_identifiers_bytes
        }

        cooled_down_key_identifiers_bytes = await self._redis.zrange(self.COOLED_DOWN_KEYS_KEY, 0, -1)  # type: ignore
        cooled_down_key_identifiers = {
            key.decode() for key in cooled_down_key_identifiers_bytes
        }

        combined_redis_key_identifiers = available_key_identifiers.union(
            cooled_down_key_identifiers
        )

        missing_from_combined = list(
            redis_all_key_identifiers - combined_redis_key_identifiers
        )
        extra_in_combined = list(
            combined_redis_key_identifiers - redis_all_key_identifiers
        )

        if missing_from_combined or extra_in_combined:
            key_manager_logger.warning(
                "Health Check 2 Failed: Mismatch between "
                "ALL_KEYS_SET_KEY and combined available/cooled key identifiers."
            )
            if missing_from_combined:
                key_manager_logger.warning(
                    "Key identifiers missing from available/cooled queues: "
                    f"{missing_from_combined}"
                )
            if extra_in_combined:
                key_manager_logger.warning(
                    f"Extra key identifiers in available/cooled queues: {extra_in_combined}"
                )
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=2,
                message="ALL_KEYS_SET_KEY and combined queues mismatch.",
                missing_keys=missing_from_combined,
                extra_keys_in_redis=extra_in_combined,
            )
        key_manager_logger.info(
            "Health Check 2 Passed: ALL_KEYS_SET_KEY and combined queues are consistent."
        )

        # 检查 3: ALL_KEYS_SET_KEY 中的每个密钥是否都有对应的 KeyState
        key_manager_logger.info(
            "Health Check 3: Verifying KeyState for each key identifier "
            "in ALL_KEYS_SET_KEY."
        )
        missing_states = []
        for key_identifier in redis_all_key_identifiers:
            state_exists = await self._redis.exists(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
            if not state_exists:
                missing_states.append(key_identifier)

        # 检查是否存在多余的 KeyState (即 Redis 中有 KeyState 但不在 ALL_KEYS_SET_KEY 中)
        all_keys_in_redis_prefix = set()
        cursor = b"0"
        while cursor:
            cursor, keys = await self._redis.scan(cursor, match=f"{self.KEY_STATE_PREFIX}*")  # type: ignore
            for key_bytes in keys:
                key_str = key_bytes.decode()
                all_keys_in_redis_prefix.add(key_str.replace(self.KEY_STATE_PREFIX, ""))
        extra_states_in_redis = list(
            all_keys_in_redis_prefix - redis_all_key_identifiers
        )

        if missing_states or extra_states_in_redis:
            key_manager_logger.warning(
                "Health Check 3 Failed: Mismatch in KeyState entries."
            )
            if missing_states:
                key_manager_logger.warning(
                    f"Key identifiers with missing states: {missing_states}"
                )
            if extra_states_in_redis:
                key_manager_logger.warning(
                    f"Extra states in Redis: {extra_states_in_redis}"
                )
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=3,
                message="KeyState entries mismatch.",
                missing_states=missing_states,
                extra_states_in_redis=extra_states_in_redis,
            )
        key_manager_logger.info(
            "Health Check 3 Passed: All KeyState entries are consistent."
        )

        key_manager_logger.info("Redis health check completed successfully.")
        return RedisHealthCheckResult(
            is_healthy=True,
            error_code=0,
            message="Redis database is healthy.",
        )

    @log_function_calls(key_manager_logger)
    async def check_redis_health(self) -> RedisHealthCheckResult:
        """
        执行 Redis 数据库的健康检查。
        此方法现在会获取锁，并调用内部的 _check_redis_health_internal 方法。
        """
        async with self._lock:
            return await self._check_redis_health_internal()

    @log_function_calls(key_manager_logger)
    async def repair_redis_database(self):
        """
        修复 Redis 数据库中的 API 密钥相关数据，直到健康检查通过。
        此方法替代 initialize_keys 的功能，并修正了原有实现中的竞争条件和逻辑错误。
        """
        # 获取分布式锁，防止多个实例同时执行修复
        is_lock_acquired = await self._redis.set("key_manager:repair_lock", "1", nx=True, ex=30)  # type: ignore
        if not is_lock_acquired:
            key_manager_logger.info("Repair lock already held. Skipping repair.")
            return

        try:
            async with self._lock:  # 添加锁保护
                if settings.FORCE_RESET_REDIS:
                    key_manager_logger.warning(
                        "FORCE_RESET_REDIS is enabled. Flushing Redis DB..."
                    )
                    await self._redis.flushdb()  # type: ignore

                # 增加循环次数限制，防止无限循环
                for i in range(5):
                    result = (
                        await self._check_redis_health_internal()
                    )  # 调用内部无锁方法
                    if result.is_healthy:
                        key_manager_logger.info(
                            f"Redis database is healthy on attempt {i + 1}."
                        )
                        break

                    key_manager_logger.warning(
                        f"Redis health check failed (code: {result.error_code}) on attempt {i + 1}. "
                        "Attempting repair..."
                    )
                    # For error_code 2, we need to fetch states before creating the pipeline
                    missing_key_states = {}
                    if result.error_code == 2 and result.missing_keys:
                        tasks = {
                            key: self._get_key_state(key) for key in result.missing_keys
                        }
                        key_states_results = await asyncio.gather(*tasks.values())
                        missing_key_states = dict(zip(tasks.keys(), key_states_results))

                    pipe = self._redis.pipeline()

                    if result.error_code == 1:
                        # 修复：配置与 ALL_KEYS_SET 不一致
                        for key_identifier in result.added_keys:
                            # 密钥在配置中但不在 Redis 中，添加它
                            initial_state = KeyState(
                                current_cool_down_seconds=self._initial_cool_down_seconds
                            )
                            pipe.hset(
                                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                                mapping=initial_state.to_redis_hash(),
                            )
                            pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
                            pipe.sadd(self.ALL_KEYS_SET_KEY, key_identifier)
                        for key_identifier in result.missing_keys:
                            # 密钥在 Redis 中但不在配置中，移除它
                            pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                            pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
                            pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
                            pipe.srem(self.ALL_KEYS_SET_KEY, key_identifier)

                    elif result.error_code == 2:
                        # 修复：ALL_KEYS_SET 与队列不一致
                        now = time.time()
                        for (
                            key_identifier,
                            key_state,
                        ) in missing_key_states.items():
                            # 密钥在 ALL_KEYS_SET 中但不在队列中
                            # 根据状态决定将其添加回可用队列还是冷却队列
                            if key_state.cool_down_until > now:
                                # 如果仍在冷却期，添加到冷却队列
                                pipe.zadd(
                                    self.COOLED_DOWN_KEYS_KEY,
                                    {key_identifier: key_state.cool_down_until},
                                )
                            else:
                                # 否则，添加回可用队列
                                pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)

                        for key_identifier in result.extra_keys_in_redis:
                            # 密钥在队列中但不在 ALL_KEYS_SET 中，从队列中移除
                            pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                            pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)

                    elif result.error_code == 3:
                        # 修复：ALL_KEYS_SET 与 KeyState 不一致
                        for key_identifier in result.missing_states:
                            # 密钥状态丢失，创建默认状态
                            initial_state = KeyState(
                                current_cool_down_seconds=self._initial_cool_down_seconds
                            )
                            pipe.hset(
                                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                                mapping=initial_state.to_redis_hash(),
                            )
                        for key_identifier in result.extra_states_in_redis:
                            # 存在多余的密钥状态，删除它
                            pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")

                    await pipe.execute()
                    key_manager_logger.info(f"Repair attempt {i + 1} finished.")
                key_manager_logger.error(
                    "Failed to repair Redis database after multiple attempts."
                )

        finally:
            # 释放锁
            await self._redis.delete("key_manager:repair_lock")  # type: ignore

    @log_function_calls(key_manager_logger)
    async def _release_cooled_down_keys(self):
        while True:
            sleep_duration = 3600  # 默认休眠时间
            try:
                async with self._lock:
                    now = time.time()
                    # 从有序集合中获取所有已冷却完毕的密钥
                    ready_to_release = await self._redis.zrangebyscore(  # type: ignore
                        self.COOLED_DOWN_KEYS_KEY, min=0, max=now, withscores=True
                    )

                    if ready_to_release:
                        pipe = self._redis.pipeline()
                        for key_bytes, cool_down_until_score in ready_to_release:
                            key_identifier = key_bytes.decode()
                            key_state = await self._get_key_state(key_identifier)

                            # 再次检查，确保状态未在获取期间被改变
                            if key_state.cool_down_until == cool_down_until_score:
                                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                                pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
                                key_state.cool_down_until = 0.0
                                key_state.request_fail_count = 0
                                pipe.hset(
                                    f"{self.KEY_STATE_PREFIX}{key_identifier}",
                                    mapping=key_state.to_redis_hash(),
                                )
                                key_manager_logger.info(
                                    f"API key identifier '{key_identifier}' reactivated."
                                )
                                pipe.zrem(
                                    self.COOLED_DOWN_KEYS_KEY, key_identifier
                                )  # 只有成功重新激活才移除
                        await pipe.execute()

                    self._wakeup_event.clear()

                    # 获取下一个冷却结束时间
                    next_cooled_key = await self._redis.zrange(  # type: ignore
                        self.COOLED_DOWN_KEYS_KEY, 0, 0, withscores=True
                    )
                    if next_cooled_key:
                        next_release_time = next_cooled_key[0][1]
                        sleep_duration = max(0.1, next_release_time - time.time())
                        # self._condition.notify_all() # 移除冗余代码

                # 在锁之外等待
                await asyncio.wait_for(
                    self._wakeup_event.wait(), timeout=sleep_duration
                )
            except asyncio.TimeoutError:
                pass  # 超时是正常的，继续下一次循环
            except asyncio.CancelledError:
                raise  # 重新引发异常以允许任务正常取消

    async def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )
            await self.repair_redis_database()  # 确保后台任务启动时初始化密钥

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    @log_function_calls(key_manager_logger)
    async def get_next_key(self) -> Optional[str]:
        # 尝试从可用队列中获取密钥，并将其原子性地移动到队列尾部，实现轮询
        # 如果队列为空，则阻塞最多5秒
        key_bytes = await self._redis.blmove(  # type: ignore
            self.AVAILABLE_KEYS_KEY, self.AVAILABLE_KEYS_KEY, 5, "LEFT", "RIGHT"
        )
        if key_bytes:
            key_identifier = key_bytes.decode()
            return self._key_map.get(key_identifier)
        else:
            await self.repair_redis_database()
            return None

    @log_function_calls(key_manager_logger)
    async def deactivate_key(self, key_identifier: str, error_type: str):
        async with self._lock:
            key_state = await self._get_key_state(key_identifier)
            if not key_state:
                return

            key_state.request_fail_count += 1

            should_cool_down = False
            if error_type in ["auth_error", "rate_limit_error"]:
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if key_state.request_fail_count >= self._api_key_failure_threshold:
                    should_cool_down = True

            if should_cool_down:
                # 使用事务确保原子性
                pipe = self._redis.pipeline()
                # 从可用队列中移除密钥
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)

                key_state.cool_down_entry_count += 1
                # 算新的冷却时间（指数退避）
                backoff_factor = 2 ** (key_state.cool_down_entry_count - 1)
                new_cool_down = self._initial_cool_down_seconds * backoff_factor
                key_state.current_cool_down_seconds = min(
                    new_cool_down, self._max_cool_down_seconds
                )
                key_state.cool_down_until = (
                    time.time() + key_state.current_cool_down_seconds
                )

                # 在事务中更新状态并添加到冷却集合
                pipe.hset(
                    f"{self.KEY_STATE_PREFIX}{key_identifier}",
                    mapping=key_state.to_redis_hash(),
                )
                pipe.zadd(
                    self.COOLED_DOWN_KEYS_KEY,
                    {key_identifier: key_state.cool_down_until},
                )
                await pipe.execute()

                self._wakeup_event.set()
                key_manager_logger.warning(
                    f"Key identifier '{key_identifier}' cooled down for "
                    f"{key_state.current_cool_down_seconds:.2f}s "
                    "due to {error_type}."
                )
            else:
                # 如果不需要冷却，仅更新失败计数
                await self._save_key_state(key_identifier, key_state)

    @log_function_calls(key_manager_logger)
    async def mark_key_success(self, key_identifier: str):
        async with self._lock:
            key_state = await self._get_key_state(key_identifier)
            if key_state:
                key_state.cool_down_entry_count = 0
                key_state.current_cool_down_seconds = self._initial_cool_down_seconds
                await self._save_key_state(key_identifier, key_state)

    @log_function_calls(key_manager_logger)
    async def record_usage(self, key_identifier: str, model: str):
        """记录指定 key 和模型的用量。"""
        async with self._lock:
            key_state = await self._get_key_state(key_identifier)
            if not key_state:
                return

            await self._reset_daily_usage_if_needed(key_state)
            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            await self._save_key_state(key_identifier, key_state)

    @log_function_calls(key_manager_logger)
    async def get_key_states(self) -> List[KeyStatusResponse]:
        """返回所有 API key 的详细状态列表。"""
        async with self._lock:
            states = []
            now = time.time()
            for key_identifier in self._api_keys:
                key_state = await self._get_key_state(key_identifier)
                if not key_state:
                    continue

                was_reset = await self._reset_daily_usage_if_needed(key_state)
                if was_reset:
                    await self._save_key_state(key_identifier, key_state)

                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    KeyStatusResponse(
                        key_identifier=key_identifier,  # 直接使用标识符
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=key_state.usage_today,
                        failure_count=key_state.request_fail_count,
                        cool_down_entry_count=key_state.cool_down_entry_count,
                        current_cool_down_seconds=key_state.current_cool_down_seconds,
                    )
                )
            return states

    def _get_key_identifier(self, key: str) -> str:
        """生成一个对日志友好且唯一的密钥标识符"""
        import hashlib

        return f"key_sha256_{hashlib.sha256(key.encode()).hexdigest()[:8]}"


# 假设 redis_client 实例在外部创建并传入
redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)
redis_key_manager = RedisKeyManager(
    redis_client,
    (settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else []),
)
