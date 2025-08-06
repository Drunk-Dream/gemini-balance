import json
import time
from typing import Dict, List, Optional, Set

import redis.asyncio as redis
from app.core.config import Settings
from app.core.logging import app_logger
from app.services.key_managers.db_manager import DBManager, KeyState


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

    async def initialize(self):
        if self.settings.FORCE_RESET_DATABASE:
            app_logger.warning("FORCE_RESET_DATABASE is enabled. Flushing Redis DB...")
            await self._redis.flushdb()  # type: ignore

    def _key_state_to_redis_hash(self, state: KeyState) -> Dict[str, str]:
        return {
            "key_identifier": state.key_identifier,
            "cool_down_until": str(state.cool_down_until),
            "request_fail_count": str(state.request_fail_count),
            "cool_down_entry_count": str(state.cool_down_entry_count),
            "current_cool_down_seconds": str(state.current_cool_down_seconds),
            "usage_today": json.dumps(state.usage_today),
            "last_usage_date": state.last_usage_date,
            "last_usage_time": str(state.last_usage_time),
        }

    def _redis_hash_to_key_state(self, data: Dict[str, str]) -> KeyState:
        return KeyState(
            key_identifier=data.get("key_identifier", ""),
            cool_down_until=float(data.get("cool_down_until", 0.0)),
            request_fail_count=int(data.get("request_fail_count", 0)),
            cool_down_entry_count=int(data.get("cool_down_entry_count", 0)),
            current_cool_down_seconds=int(
                data.get(
                    "current_cool_down_seconds", self.settings.API_KEY_COOL_DOWN_SECONDS
                )
            ),
            usage_today=json.loads(data.get("usage_today", "{}")),
            last_usage_date=data.get("last_usage_date", time.strftime("%Y-%m-%d")),
            last_usage_time=float(data.get("last_usage_time", 0.0)),
        )

    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        state_data = await self._redis.hgetall(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
        if state_data:
            decoded_data = {k.decode(): v.decode() for k, v in state_data.items()}
            return self._redis_hash_to_key_state(decoded_data)
        return None

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

    async def reactivate_key(self, key_identifier: str):
        pipe = self._redis.pipeline()
        # 尝试从冷却队列中移除
        pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        # 尝试从正在使用队列中移除 (如果之前因为某种原因没有被正确移除)
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

    async def sync_keys(self, config_keys: Set[str]):
        app_logger.info(f"Syncing keys. Config keys: {config_keys}")
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
            app_logger.info(f"Adding new keys to Redis: {keys_to_add}")
            for key_identifier in keys_to_add:
                initial_state = KeyState(
                    key_identifier=key_identifier,
                    current_cool_down_seconds=self.settings.API_KEY_COOL_DOWN_SECONDS,
                )
                pipe.hset(
                    f"{self.KEY_STATE_PREFIX}{key_identifier}",
                    mapping=self._key_state_to_redis_hash(initial_state),
                )
                pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
                pipe.sadd(self.ALL_KEYS_SET_KEY, key_identifier)
                # 确保新添加的密钥不在正在使用队列中
                pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)

        if keys_to_remove:
            app_logger.info(f"Removing old keys from Redis: {keys_to_remove}")
            for key_identifier in keys_to_remove:
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
                pipe.srem(self.IN_USE_KEYS_KEY, key_identifier)
                pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
                pipe.srem(self.ALL_KEYS_SET_KEY, key_identifier)

        await pipe.execute()
        app_logger.info("Key synchronization complete.")
