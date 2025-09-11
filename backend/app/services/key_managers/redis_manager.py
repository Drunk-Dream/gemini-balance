from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

import pytz
import redis.asyncio as redis

from backend.app.core.logging import app_logger
from backend.app.services.key_managers.db_manager import DBManager, KeyState

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class RedisDBManager(DBManager):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
        )
        self.AVAILABLE_KEYS_KEY = "key_manager:available_keys"
        self.COOLED_DOWN_KEYS_KEY = "key_manager:cooled_down_keys"
        self.IN_USE_KEYS_KEY = "key_manager:in_use_keys"
        self.KEY_STATE_PREFIX = "key_manager:state:"
        self.ALL_KEYS_SET_KEY = "key_manager:all_keys"

    def _key_state_to_redis_hash(self, state: KeyState) -> Dict[str, str]:
        return {
            "key_identifier": state.key_identifier,
            "api_key": state.api_key,
            "cool_down_until": str(state.cool_down_until),
            "request_fail_count": str(state.request_fail_count),
            "cool_down_entry_count": str(state.cool_down_entry_count),
            "current_cool_down_seconds": str(state.current_cool_down_seconds),
            "usage_today": json.dumps(state.usage_today),
            "last_usage_time": str(state.last_usage_time),
            # is_in_use 不存储在 hash 中，而是通过集合管理
        }

    def _redis_hash_to_key_state(self, data: Dict[str, str]) -> KeyState:
        return KeyState(
            key_identifier=data.get("key_identifier", ""),
            api_key=data.get("api_key", ""),
            cool_down_until=float(data.get("cool_down_until", 0.0)),
            request_fail_count=int(data.get("request_fail_count", 0)),
            cool_down_entry_count=int(data.get("cool_down_entry_count", 0)),
            current_cool_down_seconds=int(
                data.get(
                    "current_cool_down_seconds", self.settings.API_KEY_COOL_DOWN_SECONDS
                )
            ),
            usage_today=json.loads(data.get("usage_today", "{}")),
            last_usage_date="",  # 日期字段不存储在 Redis 中,需要从 last_usage_time 转换
            last_usage_time=float(data.get("last_usage_time", 0.0)),
            is_in_use=False,  # 默认值，实际状态通过 sismember 检查
        )

    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
        if state_data:
            decoded_data = {k.decode(): v.decode() for k, v in state_data.items()}
            key_state = self._redis_hash_to_key_state(decoded_data)
            # 检查密钥是否在 IN_USE_KEYS_KEY 集合中
            is_in_use = await self._redis.sismember(self.IN_USE_KEYS_KEY, key_identifier)  # type: ignore
            key_state.is_in_use = bool(is_in_use)
            eastern_tz = pytz.timezone("America/New_York")
            key_state.last_usage_date = datetime.fromtimestamp(
                key_state.last_usage_time, tz=eastern_tz
            ).strftime("%Y-%m-%d")
            return key_state
        return None

    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        state = await self.get_key_state(key_identifier)
        return state.api_key if state else None

    async def save_key_state(self, key_identifier: str, state: KeyState):
        await self._redis.hset(  # type: ignore
            f"{self.KEY_STATE_PREFIX}{key_identifier}",
            mapping=self._key_state_to_redis_hash(state),
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
        pipe = self._redis.pipeline()
        # 从可用队列中取出一个键
        pipe.lpop(self.AVAILABLE_KEYS_KEY)
        result = await pipe.execute()
        key_bytes = result[0]

        if key_bytes:
            key_identifier = key_bytes.decode()
            # 将其移动到正在使用队列并更新 last_usage_time
            pipe = self._redis.pipeline()
            pipe.sadd(self.IN_USE_KEYS_KEY, key_identifier)
            pipe.hset(
                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                "last_usage_time",
                str(time.time()),
            )
            await pipe.execute()
            return key_identifier
        return None

    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        pipe = self._redis.pipeline()
        pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
        pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)
        pipe.zadd(self.COOLED_DOWN_KEYS_KEY, {key_identifier: cool_down_until})
        await pipe.execute()

    async def get_releasable_keys(self) -> List[str]:
        now = time.time()
        ready_to_release = await self._redis.zrangebyscore(  # type: ignore
            self.COOLED_DOWN_KEYS_KEY, min=0, max=now
        )
        return [key.decode() for key in ready_to_release]

    async def get_keys_in_use(self) -> List[str]:
        """Get all keys that are currently in use."""
        keys = await self._redis.smembers(self.IN_USE_KEYS_KEY)  # type: ignore
        return [key.decode() for key in keys]

    async def reactivate_key(self, key_identifier: str):
        pipe = self._redis.pipeline()
        # 尝试从冷却队列中移除
        pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        # 确保从正在使用队列中移除
        pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)

        # 获取密钥当前状态，重置 request_fail_count
        current_state = await self.get_key_state(key_identifier)
        if current_state:
            current_state.request_fail_count = 0
            pipe.hset(
                f"{self.KEY_STATE_PREFIX}{key_identifier}",
                mapping=self._key_state_to_redis_hash(current_state),
            )

        # 将密钥重新添加到可用队列
        pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
        await pipe.execute()

    async def release_key_from_use(self, key_identifier: str):
        """Release a key from being in use, setting its is_in_use flag to 0."""
        # 从正在使用队列中移除
        await self._redis.srem(self.IN_USE_KEYS_KEY, key_identifier)  # type: ignore
        # 确保它在可用队列中 (如果它不在冷却中)
        # 注意: RedisDBManager 没有 is_in_use 字段，而是通过集合来管理状态
        # 这里的逻辑是确保它不在 IN_USE_KEYS_KEY 中，并且如果它不在 COOLED_DOWN_KEYS_KEY 中，就把它放回 AVAILABLE_KEYS_KEY
        is_cooled_down = await self._redis.zscore(
            self.COOLED_DOWN_KEYS_KEY, key_identifier
        )
        if is_cooled_down is None:  # 如果不在冷却中
            await self._redis.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)  # type: ignore

    async def add_key(self, key_identifier: str, api_key: str):
        initial_state = KeyState(
            key_identifier=key_identifier,
            api_key=api_key,
            current_cool_down_seconds=self.settings.API_KEY_COOL_DOWN_SECONDS,
        )
        pipe = self._redis.pipeline()
        pipe.hset(
            f"{self.KEY_STATE_PREFIX}{key_identifier}",
            mapping=self._key_state_to_redis_hash(initial_state),
        )
        pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
        pipe.sadd(self.ALL_KEYS_SET_KEY, key_identifier)
        await pipe.execute()
        app_logger.info(f"Added new API key '{key_identifier}' to Redis.")

    async def delete_key(self, key_identifier: str):
        pipe = self._redis.pipeline()
        pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
        pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)
        pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
        pipe.srem(self.ALL_KEYS_SET_KEY, key_identifier)
        await pipe.execute()
        app_logger.info(f"Removed API key '{key_identifier}' from Redis.")

    async def reset_key_state(self, key_identifier: str):
        state = await self.get_key_state(key_identifier)
        if state:
            state.cool_down_until = 0.0
            state.request_fail_count = 0
            state.cool_down_entry_count = 0
            state.current_cool_down_seconds = self.settings.API_KEY_COOL_DOWN_SECONDS
            state.usage_today = {}
            state.last_usage_time = time.time()
            await self.save_key_state(key_identifier, state)
            await self.reactivate_key(key_identifier)
            app_logger.info(f"Reset state for API key '{key_identifier}' in Redis.")

    async def reset_all_key_states(self):
        all_keys = await self.get_all_key_states()
        pipe = self._redis.pipeline()
        for state in all_keys:
            state.cool_down_until = 0.0
            state.request_fail_count = 0
            state.cool_down_entry_count = 0
            state.current_cool_down_seconds = self.settings.API_KEY_COOL_DOWN_SECONDS
            state.usage_today = {}
            state.last_usage_time = time.time()
            pipe.hset(
                f"{self.KEY_STATE_PREFIX}{state.key_identifier}",
                mapping=self._key_state_to_redis_hash(state),
            )
            # 确保所有键都回到可用队列，并从冷却和使用中移除
            pipe.zrem(self.COOLED_DOWN_KEYS_KEY, state.key_identifier)
            pipe.srem(self.IN_USE_KEYS_KEY, state.key_identifier)
            pipe.rpush(self.AVAILABLE_KEYS_KEY, state.key_identifier)
        await pipe.execute()
        app_logger.info("Reset state for all API keys in Redis.")
