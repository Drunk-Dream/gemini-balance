from abc import ABC, abstractmethod
from typing import List, Optional

from app.api.v1beta.schemas.auth import AuthKey


class AuthDBManager(ABC):
    """Abstract base class for authentication key database operations."""

    @abstractmethod
    async def initialize(self):
        """Initialize the database connection and tables."""
        pass

    @abstractmethod
    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        """Retrieve an authentication key by its API key."""
        pass

    @abstractmethod
    async def create_key(self, auth_key: AuthKey) -> AuthKey:
        """Create a new authentication key."""
        pass

    @abstractmethod
    async def get_all_keys(self) -> List[AuthKey]:
        """Retrieve all authentication keys."""
        pass

    @abstractmethod
    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        """Update the alias of an existing authentication key."""
        pass

    @abstractmethod
    async def delete_key(self, api_key: str) -> bool:
        """Delete an authentication key."""
        pass
