import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import app_logger
from pydantic import BaseModel, Field


class RedisHealthCheckResult(BaseModel):
    """
    Redis健康检查结果类。

    该类用于表示Redis健康检查的结果，包含健康状态、错误代码、错误信息以及相关的键状态信息。

    核心功能:
    - `is_healthy`: 表示Redis是否健康。
    - `error_code`: 错误代码，0表示健康，其他值表示不同的错误类型。
    - `message`: 错误信息，描述具体的错误原因。
    - `added_keys`: 检查过程中新增的键列表。
    - `missing_keys`: 检查过程中缺失的键列表。
    - `extra_keys_in_redis`: Redis中多余的键列表。
    - `missing_states`: 缺失的状态列表。
    - `extra_states_in_redis`: Redis中多余的状态列表。

    使用示例:

    构造函数参数:
    - `is_healthy` (bool): 表示Redis是否健康。
    - `error_code` (int, 可选): 错误代码，默认为0。0表示健康，1表示配置与ALL_KEYS_SET_KEY不匹配，
      2表示ALL_KEYS_SET_KEY与可用/冷却状态不匹配，3表示键状态不匹配。
    - `message` (str, 可选): 错误信息，默认为空字符串。
    - `added_keys` (List[str], 可选): 新增的键列表，默认为空列表。
    - `missing_keys` (List[str], 可选): 缺失的键列表，默认为空列表。
    - `extra_keys_in_redis` (List[str], 可选): Redis中多余的键列表，默认为空列表。
    - `missing_states` (List[str], 可选): 缺失的状态列表，默认为空列表。
    - `extra_states_in_redis` (List[str], 可选): Redis中多余的状态列表，默认为空列表。

    特殊使用限制或潜在的副作用:
    - 无特殊使用限制或潜在的副作用。
    """

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
        self._api_keys = api_keys
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._lock = asyncio.Lock()  # 用于保护 Redis 操作的本地锁
        self._condition = asyncio.Condition(self._lock)
        self._background_task: Optional[asyncio.Task] = None
        self._wakeup_event = asyncio.Event()

        self.AVAILABLE_KEYS_KEY = "key_manager:available_keys"
        self.COOLED_DOWN_KEYS_KEY = "key_manager:cooled_down_keys"
        self.KEY_STATE_PREFIX = "key_manager:state:"
        self.ALL_KEYS_SET_KEY = "key_manager:all_keys"  # 新增的 Redis 键

    async def _get_key_state(self, key: str) -> KeyState:
        """从 Redis 获取密钥状态，如果不存在则初始化。"""
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key}")  # type: ignore
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
                f"{self.KEY_STATE_PREFIX}{key}", mapping=initial_state.to_redis_hash()
            )
            return initial_state

    async def _save_key_state(self, key: str, state: KeyState):
        """将密钥状态保存到 Redis。"""
        await self._redis.hset(  # type: ignore
            f"{self.KEY_STATE_PREFIX}{key}", mapping=state.to_redis_hash()
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

    async def check_redis_health(self) -> RedisHealthCheckResult:
        """
        执行 Redis 数据库的健康检查。
        检查项包括：
        1. 配置中的 API 密钥与 Redis 中 ALL_KEYS_SET_KEY 的一致性。
        2. ALL_KEYS_SET_KEY 中的密钥与 AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY 的一致性。
        3. ALL_KEYS_SET_KEY 中的每个密钥是否都有对应的 KeyState。
        """
        app_logger.info("Starting Redis health check...")
        async with self._lock:
            config_keys = set(self._api_keys)

            # 检查 1: 配置中的 API 密钥与 ALL_KEYS_SET_KEY 的一致性
            app_logger.info(
                "Health Check 1: Comparing config keys " "with ALL_KEYS_SET_KEY."
            )
            redis_all_keys_bytes = await self._redis.smembers(self.ALL_KEYS_SET_KEY)  # type: ignore
            redis_all_keys = {key.decode() for key in redis_all_keys_bytes}

            added_in_config = list(config_keys - redis_all_keys)
            missing_in_config = list(redis_all_keys - config_keys)

            if added_in_config or missing_in_config:
                app_logger.warning(
                    "Health Check 1 Failed:"
                    " Mismatch between config keys and ALL_KEYS_SET_KEY."
                )
                if added_in_config:
                    app_logger.warning(
                        f"Keys to add from config: {[self.format_key(k) for k in added_in_config]}"
                    )
                if missing_in_config:
                    app_logger.warning(
                        f"Keys to remove from Redis: {[self.format_key(k) for k in missing_in_config]}"
                    )
                return RedisHealthCheckResult(
                    is_healthy=False,
                    error_code=1,
                    message="Config keys and ALL_KEYS_SET_KEY mismatch.",
                    added_keys=added_in_config,
                    missing_keys=missing_in_config,
                )
            app_logger.info(
                "Health Check 1 Passed:"
                " Config keys and ALL_KEYS_SET_KEY are consistent."
            )

            # 检查 2: ALL_KEYS_SET_KEY 中的密钥与 AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY 的一致性
            app_logger.info(
                "Health Check 2: Comparing ALL_KEYS_SET_KEY "
                "with AVAILABLE_KEYS_KEY + COOLED_DOWN_KEYS_KEY."
            )
            available_keys_bytes = await self._redis.lrange(self.AVAILABLE_KEYS_KEY, 0, -1)  # type: ignore
            available_keys = {key.decode() for key in available_keys_bytes}

            cooled_down_keys_bytes = await self._redis.zrange(self.COOLED_DOWN_KEYS_KEY, 0, -1)  # type: ignore
            cooled_down_keys = {key.decode() for key in cooled_down_keys_bytes}

            combined_redis_keys = available_keys.union(cooled_down_keys)

            missing_from_combined = list(redis_all_keys - combined_redis_keys)
            extra_in_combined = list(combined_redis_keys - redis_all_keys)

            if missing_from_combined or extra_in_combined:
                app_logger.warning(
                    "Health Check 2 Failed: Mismatch between "
                    "ALL_KEYS_SET_KEY and combined available/cooled keys."
                )
                if missing_from_combined:
                    app_logger.warning(
                        "Keys missing from available/cooled queues: "
                        f"{[self.format_key(k) for k in missing_from_combined]}"
                    )
                if extra_in_combined:
                    app_logger.warning(
                        f"Extra keys in available/cooled queues: {[self.format_key(k) for k in extra_in_combined]}"
                    )
                return RedisHealthCheckResult(
                    is_healthy=False,
                    error_code=2,
                    message="ALL_KEYS_SET_KEY and combined queues mismatch.",
                    missing_keys=missing_from_combined,
                    extra_keys_in_redis=extra_in_combined,
                )
            app_logger.info(
                "Health Check 2 Passed: ALL_KEYS_SET_KEY and combined queues are consistent."
            )

            # 检查 3: ALL_KEYS_SET_KEY 中的每个密钥是否都有对应的 KeyState
            app_logger.info(
                "Health Check 3: Verifying KeyState for each key "
                "in ALL_KEYS_SET_KEY."
            )
            missing_states = []
            for key in redis_all_keys:
                state_exists = await self._redis.exists(f"{self.KEY_STATE_PREFIX}{key}")  # type: ignore
                if not state_exists:
                    missing_states.append(key)

            # 检查是否存在多余的 KeyState (即 Redis 中有 KeyState 但不在 ALL_KEYS_SET_KEY 中)
            all_keys_in_redis_prefix_bytes = await self._redis.keys(f"{self.KEY_STATE_PREFIX}*")  # type: ignore
            all_keys_in_redis_prefix = {
                key.decode().replace(self.KEY_STATE_PREFIX, "")
                for key in all_keys_in_redis_prefix_bytes
            }
            extra_states_in_redis = list(all_keys_in_redis_prefix - redis_all_keys)

            if missing_states or extra_states_in_redis:
                app_logger.warning(
                    "Health Check 3 Failed: Mismatch in KeyState entries."
                )
                if missing_states:
                    app_logger.warning(
                        f"Keys with missing states: {[self.format_key(k) for k in missing_states]}"
                    )
                if extra_states_in_redis:
                    app_logger.warning(
                        f"Extra states in Redis: {[self.format_key(k) for k in extra_states_in_redis]}"
                    )
                return RedisHealthCheckResult(
                    is_healthy=False,
                    error_code=3,
                    message="KeyState entries mismatch.",
                    missing_states=missing_states,
                    extra_states_in_redis=extra_states_in_redis,
                )
            app_logger.info(
                "Health Check 3 Passed: All KeyState entries are consistent."
            )

            app_logger.info("Redis health check completed successfully.")
            return RedisHealthCheckResult(
                is_healthy=True,
                error_code=0,
                message="Redis database is healthy.",
            )

    async def repair_redis_database(self):
        """
        修复 Redis 数据库中的 API 密钥相关数据，直到健康检查通过。
        此方法替代 initialize_keys 的功能。
        """
        app_logger.info("Starting Redis database repair process...")
        if settings.FORCE_RESET_REDIS:
            app_logger.warning("FORCE_RESET_REDIS is enabled. Flushing Redis DB...")
            await self._redis.flushdb()  # type: ignore
            app_logger.info("Redis DB flushed.")

        while True:
            result = await self.check_redis_health()
            if result.is_healthy:
                app_logger.info("Redis database is now healthy. Repair complete.")
                break

            app_logger.info(
                f"Repair needed. Error code: {result.error_code}, "
                f"Message: {result.message}"
            )
            pipe = self._redis.pipeline()

            if result.error_code == 1:
                # 修复 1: 配置与 ALL_KEYS_SET_KEY 不一致
                app_logger.info(
                    "Repairing: Mismatch between config keys " "and ALL_KEYS_SET_KEY."
                )
                # 添加配置中新增的密钥
                for key in result.added_keys:
                    app_logger.info(
                        f"Repairing: Adding new API key '{self.format_key(key)}' from config."
                    )
                    await self._get_key_state(key)  # 确保状态被初始化
                    if not await self._redis.lpos(self.AVAILABLE_KEYS_KEY, key):  # type: ignore
                        pipe.rpush(self.AVAILABLE_KEYS_KEY, key)
                    pipe.sadd(self.ALL_KEYS_SET_KEY, key)
                # 移除 Redis 中多余的密钥
                for key in result.missing_keys:
                    app_logger.info(
                        f"Repairing: Removing obsolete API key '{self.format_key(key)}' from Redis."
                    )
                    pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key)
                    pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key)
                    pipe.delete(f"{self.KEY_STATE_PREFIX}{key}")
                    pipe.srem(self.ALL_KEYS_SET_KEY, key)
            elif result.error_code == 2:
                # 修复 2: ALL_KEYS_SET_KEY 与可用/冷却队列不一致
                app_logger.info(
                    "Repairing: Mismatch between ALL_KEYS_SET_KEY "
                    "and available/cooled queues."
                )
                # 将 ALL_KEYS_SET_KEY 中缺失的 key 添加到可用队列
                for key in result.missing_keys:
                    app_logger.info(
                        f"Repairing: Adding missing key '{self.format_key(key)}' "
                        "to available queue and "
                        "resetting its state."
                    )
                    pipe.delete(f"{self.KEY_STATE_PREFIX}{key}")
                    await self._get_key_state(key)
                    if not await self._redis.lpos(self.AVAILABLE_KEYS_KEY, key):  # type: ignore
                        pipe.rpush(self.AVAILABLE_KEYS_KEY, key)
                # 移除可用/冷却队列中多余的 key
                for key in result.extra_keys_in_redis:
                    app_logger.info(
                        f"Repairing: Removing extra key '{self.format_key(key)}' "
                        "from available/cooled queues."
                    )
                    pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key)
                    pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key)
            elif result.error_code == 3:
                # 修复 3: KeyState 不一致
                app_logger.info("Repairing: Mismatch in KeyState entries.")
                # 为缺失 KeyState 的 key 初始化状态
                for key in result.missing_states:
                    app_logger.info(
                        f"Repairing: Initializing missing KeyState for '{self.format_key(key)}'."
                    )
                    await self._get_key_state(key)  # _get_key_state 会自动初始化并保存
                # 删除 Redis 中多余的 KeyState
                for key in result.extra_states_in_redis:
                    app_logger.info(
                        f"Repairing: Deleting extra KeyState for '{self.format_key(key)}'."
                    )
                    pipe.delete(f"{self.KEY_STATE_PREFIX}{key}")

            await pipe.execute()
            app_logger.info("Repair step executed. Re-checking health...")

    async def _release_cooled_down_keys(self):
        while True:
            sleep_duration = 3600  # 默认休眠时间
            try:
                async with self._lock:
                    now = time.time()
                    app_logger.debug(f"Background task: Current time is {now}")
                    # 从有序集合中获取所有已冷却完毕的密钥
                    ready_to_release = await self._redis.zrangebyscore(  # type: ignore
                        self.COOLED_DOWN_KEYS_KEY, min=0, max=now, withscores=True
                    )

                    if ready_to_release:
                        pipe = self._redis.pipeline()
                        for key_bytes, cool_down_until_score in ready_to_release:
                            key = key_bytes.decode()
                            key_state = await self._get_key_state(key)

                            # 再次检查，确保状态未在获取期间被改变
                            if key_state.cool_down_until == cool_down_until_score:
                                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key)
                                pipe.rpush(self.AVAILABLE_KEYS_KEY, key)
                                key_state.cool_down_until = 0.0
                                key_state.request_fail_count = 0
                                pipe.hset(
                                    f"{self.KEY_STATE_PREFIX}{key}",
                                    mapping=key_state.to_redis_hash(),
                                )
                                app_logger.info(
                                    f"API key '{self.format_key(key)}' reactivated."
                                )
                            # 无论如何都从冷却集合中移除
                            pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key)
                        await pipe.execute()
                        app_logger.debug("Background task: Pipeline executed.")

                    self._wakeup_event.clear()

                    # 获取下一个冷却结束时间
                    next_cooled_key = await self._redis.zrange(  # type: ignore
                        self.COOLED_DOWN_KEYS_KEY, 0, 0, withscores=True
                    )
                    if next_cooled_key:
                        next_release_time = next_cooled_key[0][1]
                        sleep_duration = max(0.1, next_release_time - time.time())
                        app_logger.debug(f"Next key release in {sleep_duration:.2f}s.")
                        self._condition.notify_all()
                    else:
                        sleep_duration = 3600  # 如果没有key，则长时间休眠
                        app_logger.debug("No cooled down keys, sleeping for 3600s.")

                # 在锁之外等待
                app_logger.debug(f"Waiting for {sleep_duration:.2f}s or wakeup event.")
                await asyncio.wait_for(
                    self._wakeup_event.wait(), timeout=sleep_duration
                )
                app_logger.debug("Woke up by event.")
            except asyncio.TimeoutError:
                app_logger.debug("Woke up by timeout.")
                pass  # 超时是正常的，继续下一次循环
            except asyncio.CancelledError:
                app_logger.info(
                    "Background task `_release_cooled_down_keys` cancelled."
                )
                raise  # 重新引发异常以允许任务正常取消

    async def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )
            await self.repair_redis_database()  # 确保在后台任务启动时初始化密钥

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            # 尝试从可用队列中获取密钥，如果队列为空则阻塞
            key_bytes = await self._redis.blpop([self.AVAILABLE_KEYS_KEY], timeout=10)  # type: ignore
            if key_bytes:
                key = key_bytes[1].decode()  # blpop 返回 (list_name, key_value)
                # 将密钥重新放回队列尾部，实现轮询
                await self._redis.rpush(self.AVAILABLE_KEYS_KEY, key)  # type: ignore
                return key
            else:
                app_logger.warning("Timeout waiting for an available key.")
                await self.repair_redis_database()
                return None

    async def deactivate_key(self, key: str, error_type: str):
        async with self._lock:
            key_state = await self._get_key_state(key)
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
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key)

                key_state.cool_down_entry_count += 1
                # 计算新的冷却时间（指数退避）
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
                    f"{self.KEY_STATE_PREFIX}{key}", mapping=key_state.to_redis_hash()
                )
                pipe.zadd(self.COOLED_DOWN_KEYS_KEY, {key: key_state.cool_down_until})
                await pipe.execute()

                self._wakeup_event.set()
                app_logger.warning(
                    f"Key '{self.format_key(key)}' cooled down for "
                    f"{key_state.current_cool_down_seconds:.2f}s "
                    "due to {error_type}."
                )
            else:
                # 如果不需要冷却，仅更新失败计数
                await self._save_key_state(key, key_state)

    async def mark_key_success(self, key: str):
        async with self._lock:
            key_state = await self._get_key_state(key)
            if key_state:
                key_state.cool_down_entry_count = 0
                key_state.current_cool_down_seconds = self._initial_cool_down_seconds
                await self._save_key_state(key, key_state)

    async def record_usage(self, key: str, model: str):
        """记录指定 key 和模型的用量。"""
        async with self._lock:
            key_state = await self._get_key_state(key)
            if not key_state:
                return

            await self._reset_daily_usage_if_needed(key_state)
            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            await self._save_key_state(key, key_state)
            app_logger.debug(
                f"Key '{self.format_key(key)}' usage for model '{model}': "
                f"{key_state.usage_today[model]}"
            )

    async def get_key_states(self) -> List[KeyStatusResponse]:
        """返回所有 API key 的详细状态列表。"""
        async with self._lock:
            states = []
            now = time.time()
            for key in self._api_keys:
                key_state = await self._get_key_state(key)
                if not key_state:
                    continue

                was_reset = await self._reset_daily_usage_if_needed(key_state)
                if was_reset:
                    await self._save_key_state(key, key_state)

                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    KeyStatusResponse(
                        key_identifier=f"{self.format_key(key)}",
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=key_state.usage_today,
                        failure_count=key_state.request_fail_count,
                        cool_down_entry_count=key_state.cool_down_entry_count,
                        current_cool_down_seconds=key_state.current_cool_down_seconds,
                    )
                )
            return states

    def format_key(self, key: str) -> str:
        return f"...{key[-4:]}"


# 假设 redis_client 实例在外部创建并传入
redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)
redis_key_manager = RedisKeyManager(
    redis_client,
    (settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else []),
)
