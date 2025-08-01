import json
import time
from typing import Dict, List, Optional, Set

import redis.asyncio as redis
from app.core.config import Settings
from app.core.logging import setup_debug_logger
from app.services.key_managers.db_manager import DBManager, KeyState
from pydantic import BaseModel, Field

key_manager_logger = setup_debug_logger("redis_key_manager")


class RedisHealthCheckResult(BaseModel):
    is_healthy: bool
    error_code: int = 0
    message: str = ""
    added_keys: List[str] = Field(default_factory=list)
    missing_keys: List[str] = Field(default_factory=list)
    extra_keys_in_redis: List[str] = Field(default_factory=list)
    missing_states: List[str] = Field(default_factory=list)
    extra_states_in_redis: List[str] = Field(default_factory=list)


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
        self.KEY_STATE_PREFIX = "key_manager:state:"
        self.ALL_KEYS_SET_KEY = "key_manager:all_keys"

    async def initialize(self):
        await self.repair_redis_database()

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
        key_bytes = await self._redis.blmove(  # type: ignore
            self.AVAILABLE_KEYS_KEY, self.AVAILABLE_KEYS_KEY, 5, "LEFT", "RIGHT"
        )
        if key_bytes:
            return key_bytes.decode()
        else:
            await self.repair_redis_database()
            return None

    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        pipe = self._redis.pipeline()
        pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
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
        pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
        await pipe.execute()

    async def sync_keys(self, config_keys: Set[str]):
        # This is handled by the repair mechanism
        pass

    async def repair_redis_database(self):
        is_lock_acquired = await self._redis.set(  # type: ignore
            "key_manager:repair_lock", "1", nx=True, ex=30
        )
        if not is_lock_acquired:
            key_manager_logger.info("Repair lock already held. Skipping repair.")
            return

        try:
            if self.settings.FORCE_RESET_REDIS:
                key_manager_logger.warning(
                    "FORCE_RESET_REDIS is enabled. Flushing Redis DB..."
                )
                await self._redis.flushdb()  # type: ignore

            for i in range(5):
                result = await self._check_redis_health_internal()
                if result.is_healthy:
                    key_manager_logger.info(
                        f"Redis database is healthy on attempt {i + 1}."
                    )
                    break

                key_manager_logger.warning(
                    f"Redis health check failed (code: {result.error_code}) on attempt {i + 1}. "
                    "Attempting repair..."
                )
                await self._perform_repair(result)
            else:
                key_manager_logger.error(
                    "Failed to repair Redis database after multiple attempts."
                )
        finally:
            await self._redis.delete("key_manager:repair_lock")  # type: ignore

    async def _perform_repair(self, result: RedisHealthCheckResult):
        pipe = self._redis.pipeline()
        if result.error_code == 1:
            for key_identifier in result.added_keys:
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
            for key_identifier in result.missing_keys:
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
                pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
                pipe.srem(self.ALL_KEYS_SET_KEY, key_identifier)
        elif result.error_code == 2:
            now = time.time()
            for key_identifier in result.missing_keys:
                key_state = await self.get_key_state(key_identifier)
                if key_state and key_state.cool_down_until > now:
                    pipe.zadd(
                        self.COOLED_DOWN_KEYS_KEY,
                        {key_identifier: key_state.cool_down_until},
                    )
                else:
                    pipe.rpush(self.AVAILABLE_KEYS_KEY, key_identifier)
            for key_identifier in result.extra_keys_in_redis:
                pipe.lrem(self.AVAILABLE_KEYS_KEY, 0, key_identifier)
                pipe.zrem(self.COOLED_DOWN_KEYS_KEY, key_identifier)
        elif result.error_code == 3:
            for key_identifier in result.missing_states:
                initial_state = RedisKeyState(
                    key_identifier=key_identifier,
                    current_cool_down_seconds=self.settings.API_KEY_COOL_DOWN_SECONDS,
                )
                pipe.hset(
                    f"{self.KEY_STATE_PREFIX}{key_identifier}",
                    mapping=initial_state.to_redis_hash(),
                )
            for key_identifier in result.extra_states_in_redis:
                pipe.delete(f"{self.KEY_STATE_PREFIX}{key_identifier}")
        await pipe.execute()

    async def _check_redis_health_internal(self) -> RedisHealthCheckResult:
        config_key_identifiers = set(self.settings.GOOGLE_API_KEYS or [])

        redis_all_key_identifiers_bytes = await self._redis.smembers(self.ALL_KEYS_SET_KEY)  # type: ignore
        redis_all_key_identifiers = {
            key.decode() for key in redis_all_key_identifiers_bytes
        }

        added_in_config = list(config_key_identifiers - redis_all_key_identifiers)
        missing_in_config = list(redis_all_key_identifiers - config_key_identifiers)

        if added_in_config or missing_in_config:
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=1,
                message="Config key identifiers and ALL_KEYS_SET_KEY mismatch.",
                added_keys=added_in_config,
                missing_keys=missing_in_config,
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
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=2,
                message="ALL_KEYS_SET_KEY and combined queues mismatch.",
                missing_keys=missing_from_combined,
                extra_keys_in_redis=extra_in_combined,
            )

        missing_states = []
        for key_identifier in redis_all_key_identifiers:
            state_exists = await self._redis.exists(f"{self.KEY_STATE_PREFIX}{key_identifier}")  # type: ignore
            if not state_exists:
                missing_states.append(key_identifier)

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
            return RedisHealthCheckResult(
                is_healthy=False,
                error_code=3,
                message="KeyState entries mismatch.",
                missing_states=missing_states,
                extra_states_in_redis=extra_states_in_redis,
            )

        return RedisHealthCheckResult(is_healthy=True)
