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
        self.hash_key_name = "auth_keys"  # Use a single hash key for all AuthKeys

    async def initialize(self):
        """Initializes the Redis connection (no specific table creation needed for Redis)."""
        # Ping the Redis server to ensure connection is active
        await self.redis_client.ping()

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        alias = await self.redis_client.hget(self.hash_key_name, api_key)  # type: ignore
        if alias:
            return AuthKey(api_key=api_key, alias=alias)
        return None

    async def create_key(self, auth_key: AuthKey) -> AuthKey:
        await self.redis_client.hset(
            self.hash_key_name, auth_key.api_key, auth_key.alias
        )  # type: ignore
        return auth_key

    async def get_all_keys(self) -> List[AuthKey]:
        all_key_aliases = await self.redis_client.hgetall(self.hash_key_name)  # type: ignore
        keys = []
        for api_key, alias in all_key_aliases.items():
            keys.append(AuthKey(api_key=api_key, alias=alias))
        return keys

    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        # Check if the key exists before updating
        exists = await self.redis_client.hexists(self.hash_key_name, api_key)  # type: ignore
        if exists:
            await self.redis_client.hset(self.hash_key_name, api_key, new_alias)  # type: ignore
            return AuthKey(api_key=api_key, alias=new_alias)
        return None

    async def delete_key(self, api_key: str) -> bool:
        result = await self.redis_client.hdel(self.hash_key_name, api_key)  # type: ignore
        return result > 0
