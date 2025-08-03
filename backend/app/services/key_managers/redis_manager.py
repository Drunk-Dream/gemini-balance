import json
import time
import typing  # 导入 typing 模块
from typing import Dict, List, Optional, Set

import redis.asyncio as redis
from app.core.config import Settings
from app.core.logging import setup_debug_logger
from app.services.key_managers.db_manager import DBManager, KeyState

key_manager_logger = setup_debug_logger("redis_key_manager")


class RedisKeyState(KeyState):
    def to_redis_hash(self) -> Dict[str, str]:
        return {
            "key_identifier": self.key_identifier,
            "cool_down_until": str(self.cool_down_until),
            "request_fail_count": str(self.request_fail_count),
            "cool_down_entry_count": str(self.cool_down_entry_count),
            "current_cool_down_seconds": str(self.current_cool_down_seconds),
            "usage_today": json.dumps(self.usage_today),
            "last_usage_date": self.last_usage_date,
            "last_usage_time": str(self.last_usage_time),
        }

    @classmethod
    def from_redis_hash(
        cls, data: Dict[str, str], settings: Settings
    ) -> "RedisKeyState":
        return cls(
            key_identifier=data.get("key_identifier", ""),
            cool_down_until=float(data.get("cool_down_until", 0.0)),
            request_fail_count=int(data.get("request_fail_count", 0)),
            cool_down_entry_count=int(data.get("cool_down_entry_count", 0)),
            current_cool_down_seconds=int(
                data.get(
                    "current_cool_down_seconds", settings.API_KEY_COOL_DOWN_SECONDS
                )
            ),
            usage_today=json.loads(data.get("usage_today", "{}")),
            last_usage_date=data.get("last_usage_date", time.strftime("%Y-%m-%d")),
            last_usage_time=float(data.get("last_usage_time", 0.0)),
        )


class RedisDBManager(DBManager):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
        )
        self.AVAILABLE_KEYS_KEY = "key_manager:available_keys"
        self.COOLED_DOWN_KEYS_KEY = "key_manager:cooled_down_keys"
        self.IN_USE_KEYS_KEY = "key_manager:in_use_keys"  # 新增的键
        self.KEY_STATE_PREFIX = "key_manager:state:"
        self.ALL_KEYS_SET_KEY = "key_manager:all_keys"

    async def initialize(self):
        if self.settings.FORCE_RESET_DATABASE:
            key_manager_logger.warning(
                "FORCE_RESET_DATABASE is enabled. Flushing Redis DB..."
            )
            await self._redis.flushdb()  # type: ignore

    async def get_key_state(self, key_identifier: str) -> Optional[RedisKeyState]:
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
        if state_data:
            decoded_data = {k.decode(): v.decode() for k, v in state_data.items()}
            return RedisKeyState.from_redis_hash(decoded_data, self.settings)
        return None

    async def save_key_state(self, key_identifier: str, state: KeyState):
        if isinstance(state, RedisKeyState):
            await self._redis.hset(  # type: ignore
                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                mapping=state.to_redis_hash(),
            )

    async def get_all_key_states(self) -> List[KeyState]:
        keys = await self._redis.smembers(self.ALL_KEYS_SET_KEY)  # type: ignore
        states = []
        for key_bytes in keys:
            key_identifier = key_bytes.decode()
            state = await self.get_key_state(key_identifier)
            if state:
                states.append(state)
        return states

    async def get_next_available_key(self) -> Optional[str]:
        # 从可用队列中取出一个键，并将其移动到正在使用队列
        key_bytes = await self._redis.lpop(self.AVAILABLE_KEYS_KEY)  # type: ignore
        if key_bytes is not None:
            key_identifier = key_bytes.decode()  # type: ignore
            await self._redis.sadd(self.IN_USE_KEYS_KEY, key_identifier)  # type: ignore
            return key_identifier
        return None

    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        pipe = self._redis.pipeline()
        pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)  # 从可用队列中移除
        pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)  # 从正在使用队列中移除
        pipe.zadd(
            self.COOLED_DOWN_KEYS_KEY, {key_identifier: cool_down_until}
        )  # 添加到冷却队列
        await pipe.execute()

    async def get_releasable_keys(self) -> List[str]:
        now = time.time()
        ready_to_release = await self._redis.zrangebyscore(  # type: ignore
            self.COOLED_DOWN_KEYS_KEY, min=0, max=now
        )
        # 明确 cast 为 List[bytes]
        return [key.decode() for key in typing.cast(List[bytes], ready_to_release)]

    async def reactivate_key(self, key_identifier: str):
        pipe = self._redis.pipeline()
        # 尝试从冷却队列中移除
        pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        # 尝试从正在使用队列中移除 (如果之前因为某种原因没有被正确移除)
        pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)
        # 将密钥重新添加到可用队列
        pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
        await pipe.execute()

    async def sync_keys(self, config_keys: Set[str]):
        key_manager_logger.info(f"Syncing keys. Config keys: {config_keys}")
        pipe = self._redis.pipeline()

        # 获取 Redis 中所有已知的密钥
        redis_all_key_identifiers_bytes = await self._redis.smembers(self.ALL_KEYS_SET_KEY)  # type: ignore
        redis_all_key_identifiers = {
            key.decode() for key in redis_all_key_identifiers_bytes
        }

        # 找出需要添加的密钥 (配置中有，Redis 中没有)
        keys_to_add = config_keys - redis_all_key_identifiers
        # 找出需要移除的密钥 (Redis 中有，配置中没有)
        keys_to_remove = redis_all_key_identifiers - config_keys

        if keys_to_add:
            key_manager_logger.info(f"Adding new keys to Redis: {keys_to_add}")
            for key_identifier in keys_to_add:
                initial_state = RedisKeyState(
                    key_identifier=key_identifier,
                    current_cool_down_seconds=self.settings.API_KEY_COOL_DOWN_SECONDS,
                )
                pipe.hset(
                    f"{self.KEY_STATE_PREFIX}{key_identifier}",
                    mapping=initial_state.to_redis_hash(),
                )
                pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
                pipe.sadd(self.ALL_KEYS_SET_KEY, key_identifier)
                # 确保新添加的密钥不在正在使用队列中
                pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)

        if keys_to_remove:
            key_manager_logger.info(f"Removing old keys from Redis: {keys_to_remove}")
            for key_identifier in keys_to_remove:
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
                pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)  # 从正在使用队列中移除
                pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
                pipe.srem(self.ALL_KEYS_SET_KEY, key_identifier)

        await pipe.execute()
        key_manager_logger.info("Key synchronization complete.")
