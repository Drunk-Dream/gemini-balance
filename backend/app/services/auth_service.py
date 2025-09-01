from typing import List, Optional

from backend.app.api.management.schemas.auth import AuthKey, AuthKeyCreate
from backend.app.services import auth_key_manager


class AuthService:
    """
    Service class for managing authentication keys.
    Encapsulates business logic for key creation, retrieval, update, and deletion.
    """

    def __init__(self):
        self.db_manager = auth_key_manager

    async def initialize(self):
        """Initializes the underlying database manager."""
        await self.db_manager.initialize()

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        """Retrieves an authentication key by its API key and increments its call count."""
        key = await self.db_manager.get_key(api_key)
        if key:
            await self.db_manager.increment_call_count(api_key)
        return key

    async def create_key(self, key_create: AuthKeyCreate) -> AuthKey:
        """Creates a new authentication key."""
        auth_key = AuthKey(alias=key_create.alias)
        return await self.db_manager.create_key(auth_key)

    async def get_keys(self) -> List[AuthKey]:
        """Retrieves all authentication keys."""
        return await self.db_manager.get_all_keys()

    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        """Updates the alias of an existing authentication key."""
        return await self.db_manager.update_key_alias(api_key, new_alias)

    async def delete_key(self, api_key: str) -> bool:
        """Deletes an authentication key."""
        return await self.db_manager.delete_key(api_key)
