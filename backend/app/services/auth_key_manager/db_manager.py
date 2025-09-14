from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from backend.app.api.management.schemas.auth_keys import AuthKey


class AuthDBManager(ABC):
    """Abstract base class for authentication key database operations."""

    @abstractmethod
    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        """Retrieve an authentication key by its API key."""
        raise NotImplementedError

    @abstractmethod
    async def create_key(self, auth_key: AuthKey) -> AuthKey:
        """Create a new authentication key."""
        raise NotImplementedError

    @abstractmethod
    async def get_all_keys(self) -> List[AuthKey]:
        """Retrieve all authentication keys."""
        raise NotImplementedError

    @abstractmethod
    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        """Update the alias of an existing authentication key."""
        raise NotImplementedError

    @abstractmethod
    async def delete_key(self, api_key: str) -> bool:
        """Delete an authentication key."""
        raise NotImplementedError

    @abstractmethod
    async def increment_call_count(self, api_key: str):
        """Increment the call count for a given API key."""
        raise NotImplementedError
