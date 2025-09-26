import time
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class KeyState(BaseModel):
    key_identifier: str
    api_key: str  # 新增字段
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    last_usage_time: float = Field(default_factory=lambda: time.time())
    is_in_use: bool = False  # 新增字段，指示key是否在使用中


class DBManager(ABC):
    """
    Abstract class for database operations for the key manager.
    """

    @abstractmethod
    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        """Get the state of a single key."""
        raise NotImplementedError

    @abstractmethod
    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        """Get the raw API key from its identifier."""
        raise NotImplementedError

    @abstractmethod
    async def save_key_state(self, key_identifier: str, state: "KeyState"):
        """Save the state of a single key."""
        raise NotImplementedError

    @abstractmethod
    async def get_all_key_states(self) -> List[KeyState]:
        """Get the states of all keys."""
        raise NotImplementedError

    @abstractmethod
    async def get_next_available_key(self) -> Optional[str]:
        """Get the next available key identifier."""
        raise NotImplementedError

    @abstractmethod
    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        """Move a key to the cooldown queue."""
        raise NotImplementedError

    @abstractmethod
    async def get_releasable_keys(self) -> List[str]:
        """Get all keys that have finished their cooldown."""
        raise NotImplementedError

    @abstractmethod
    async def get_keys_in_use(self) -> List[str]:
        """Get all keys that are currently in use."""
        raise NotImplementedError

    @abstractmethod
    async def get_available_keys_count(self) -> int:
        """Get the count of available keys."""
        raise NotImplementedError

    @abstractmethod
    async def reactivate_key(self, key_identifier: str):
        """Reactivate a key, moving it back to the available queue."""
        raise NotImplementedError

    @abstractmethod
    async def release_key_from_use(self, key_identifier: str):
        """Release a key from being in use, setting its is_in_use flag to 0."""
        raise NotImplementedError

    @abstractmethod
    async def move_to_use(self, key_identifier: str):
        """Mark a key as in use and update its last usage time."""
        raise NotImplementedError

    @abstractmethod
    async def add_key(self, key_identifier: str, api_key: str):
        """Add a new API key to the database."""
        raise NotImplementedError

    @abstractmethod
    async def delete_key(self, key_identifier: str):
        """Delete an API key from the database."""
        raise NotImplementedError

    @abstractmethod
    async def reset_key_state(self, key_identifier: str):
        """Reset the state of a specific API key."""
        raise NotImplementedError

    @abstractmethod
    async def reset_all_key_states(self):
        """Reset the state of all API keys."""
        raise NotImplementedError

    @abstractmethod
    async def get_min_cool_down_until(self) -> Optional[float]:
        """Get the minimum cool_down_until value among all cooled-down keys."""
        raise NotImplementedError
