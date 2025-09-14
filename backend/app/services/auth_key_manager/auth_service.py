from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from backend.app.api.management.schemas.auth_keys import AuthKey
from backend.app.services.auth_key_manager.db_manager import AuthDBManager

if TYPE_CHECKING:
    from backend.app.api.management.schemas.auth_keys import AuthKeyCreate


class AuthService:
    """
    Service class for managing authentication keys.
    Encapsulates business logic for key creation, retrieval, update, and deletion.
    """

    def __init__(self, db_manager: AuthDBManager):
        self._db_manager = db_manager

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        """Retrieves an authentication key by its API key and increments its call count."""
        key = await self._db_manager.get_key(api_key)
        if key:
            await self._db_manager.increment_call_count(api_key)
        return key

    async def create_key(self, key_create: AuthKeyCreate) -> AuthKey:
        """Creates a new authentication key."""
        auth_key = AuthKey(alias=key_create.alias)
        return await self._db_manager.create_key(auth_key)

    async def get_keys(self) -> List[AuthKey]:
        """Retrieves all authentication keys."""
        return await self._db_manager.get_all_keys()

    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        """Updates the alias of an existing authentication key."""
        return await self._db_manager.update_key_alias(api_key, new_alias)

    async def delete_key(self, api_key: str) -> bool:
        """Deletes an authentication key."""
        return await self._db_manager.delete_key(api_key)
