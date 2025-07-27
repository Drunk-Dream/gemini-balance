import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import app_logger
from pydantic import BaseModel, Field


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

    async def _get_key_state(self, key: str) -> KeyState:
        """从 Redis 获取密钥状态，如果不存在则初始化。"""
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key}")  # type: ignore # noqa: E501
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

    async def initialize_keys(self):
        """初始化 Redis 中的密钥列表和状态。"""
        async with self._lock:
            # 检查可用密钥列表是否已初始化
            if await self._redis.exists(self.AVAILABLE_KEYS_KEY):  # type: ignore
                app_logger.info("Redis key manager already initialized.")
                # 确保所有初始API Key都在Redis中被记录状态
                for key in self._api_keys:
                    await self._get_key_state(key)
                return

            app_logger.info("Initializing Redis key manager...")
            # 清空旧数据（如果存在）
            await self._redis.delete(self.AVAILABLE_KEYS_KEY, self.COOLED_DOWN_KEYS_KEY)  # type: ignore # noqa: E501
            for key in self._api_keys:
                await self._redis.delete(f"{self.KEY_STATE_PREFIX}{key}")  # type: ignore # noqa: E501

            # 将所有密钥添加到可列表并初始化状态
            for key in self._api_keys:
                await self._redis.rpush(self.AVAILABLE_KEYS_KEY, key)  # type: ignore
                initial_state = KeyState(
                    current_cool_down_seconds=self._initial_cool_down_seconds
                )
                await self._save_key_state(key, initial_state)
            app_logger.info("Redis key manager initialized successfully.")

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
                                app_logger.info(f"API key '...{key[-4:]}' reactivated.")
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
            await self.initialize_keys()  # 确保在后台任务启动时初始化密钥

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            # 尝试从可用队列中获取密钥，如果队列为空则阻塞
            key_bytes = await self._redis.blpop([self.AVAILABLE_KEYS_KEY], timeout=5)  # type: ignore # noqa: E501
            if key_bytes:
                key = key_bytes[1].decode()  # blpop 返回 (list_name, key_value)
                # 将密钥重新放回队列尾部，实现轮询
                await self._redis.rpush(self.AVAILABLE_KEYS_KEY, key)  # type: ignore # noqa: E501
                return key
            else:
                app_logger.warning("Timeout waiting for an available key.")
                # 如果超时，直接返回 None，不等待冷却中的密钥
                app_logger.error("No API keys available after timeout.")
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
                    f"Key '...{key[-4:]}' cooled down for "
                    f"{key_state.current_cool_down_seconds:.2f}s "
                    f"due to {error_type}."
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

            today_str = datetime.now().strftime("%Y-%m-%d")

            if key_state.last_usage_date != today_str:
                key_state.usage_today = {}
                key_state.last_usage_date = today_str

            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            await self._save_key_state(key, key_state)
            app_logger.debug(
                f"Key '...{key[-4:]}' usage for model '{model}': "
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

                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    KeyStatusResponse(
                        key_identifier=f"...{key[-4:]}",
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=key_state.usage_today,
                        failure_count=key_state.request_fail_count,
                        cool_down_entry_count=key_state.cool_down_entry_count,
                        current_cool_down_seconds=key_state.current_cool_down_seconds,
                    )
                )
            return states


# 假设 redis_client 实例在外部创建并传入
redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)
redis_key_manager = RedisKeyManager(
    redis_client,
    settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else [],
)
