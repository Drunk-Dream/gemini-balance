from typing import List, Optional

import redis.asyncio as redis
from app.api.v1beta.schemas.auth import AuthKey
from app.core.config import Settings
from app.services.auth_key_manager.db_manager import AuthDBManager


class RedisAuthDBManager(AuthDBManager):
    """Redis implementation of the AuthDBManager for authentication key storage."""

    def __init__(self, settings: Settings):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self.auth_keys_hash = "auth_keys"  # Use a single hash key for AuthKey alias
        self.call_count_hash = "auth_key_call_counts"  # Separate hash for call counts

    async def initialize(self):
        """Initializes the Redis connection (no specific table creation needed for Redis)."""
        # Ping the Redis server to ensure connection is active
        await self.redis_client.ping()

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        alias = await self.redis_client.hget(self.auth_keys_hash, api_key)  # type: ignore
        if alias:
            call_count_str = await self.redis_client.hget(self.call_count_hash, api_key)  # type: ignore
            call_count = int(call_count_str) if call_count_str else 0
            return AuthKey(api_key=api_key, alias=alias, call_count=call_count)
        return None

    async def create_key(self, auth_key: AuthKey) -> AuthKey:
        await self.redis_client.hset(
            self.auth_keys_hash, auth_key.api_key, auth_key.alias
        )  # type: ignore
        await self.redis_client.hset(
            self.call_count_hash, auth_key.api_key, str(auth_key.call_count)
        )  # type: ignore
        return auth_key

    async def get_all_keys(self) -> List[AuthKey]:
        all_key_aliases = await self.redis_client.hgetall(self.auth_keys_hash)  # type: ignore
        all_call_counts = await self.redis_client.hgetall(self.call_count_hash)  # type: ignore
        keys = []
        for api_key, alias in all_key_aliases.items():
            call_count = int(all_call_counts.get(api_key, 0))
            keys.append(AuthKey(api_key=api_key, alias=alias, call_count=call_count))
        return keys

    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        # Check if the key exists before updating
        exists = await self.redis_client.hexists(self.auth_keys_hash, api_key)  # type: ignore
        if exists:
            await self.redis_client.hset(self.auth_keys_hash, api_key, new_alias)  # type: ignore
            call_count_str = await self.redis_client.hget(self.call_count_hash, api_key)  # type: ignore
            call_count = int(call_count_str) if call_count_str else 0
            return AuthKey(api_key=api_key, alias=new_alias, call_count=call_count)
        return None

    async def delete_key(self, api_key: str) -> bool:
        result_alias = await self.redis_client.hdel(self.auth_keys_hash, api_key)  # type: ignore
        result_count = await self.redis_client.hdel(self.call_count_hash, api_key)  # type: ignore
        return result_alias > 0 or result_count > 0

    async def increment_call_count(self, api_key: str):
        await self.redis_client.hincrby(self.call_count_hash, api_key, 1)  # type: ignore
