from abc import ABC, abstractmethod
from typing import List, Optional

from backend.app.services.request_key_manager.schemas import (
    KeyCounts,
    KeyState,
    ApiKey,
)


class DBManager(ABC):
    """
    Abstract class for database operations for the key manager.
    """

    @staticmethod
    def key_to_brief(key: str) -> str:
        return key[:4] + "..." + key[-4:]

    # --------------- Key Management ---------------
    @abstractmethod
    async def add_key(self, key: ApiKey):
        """Add a new API key to the database."""
        raise NotImplementedError

    @abstractmethod
    async def delete_key(self, key_identifier: str) -> Optional[str]:
        """Delete an API key from the database."""
        raise NotImplementedError

    @abstractmethod
    async def reset_key_state(self, key_identifier: str) -> Optional[str]:
        """Reset the state of a specific API key."""
        raise NotImplementedError

    @abstractmethod
    async def reset_all_key_states(self):
        """Reset the state of all API keys."""
        raise NotImplementedError

    # --------------- Get Key State ---------------
    @abstractmethod
    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        """Get the state of a single key."""
        raise NotImplementedError

    @abstractmethod
    async def get_all_key_states(self) -> List[KeyState]:
        """Get the states of all keys."""
        raise NotImplementedError

    @abstractmethod
    async def get_and_lock_next_available_key(self) -> Optional[ApiKey]:
        """Atomically get the next available key and mark it as in use."""
        raise NotImplementedError

    @abstractmethod
    async def get_releasable_keys(self) -> List[ApiKey]:
        """Get all keys that have finished their cooldown."""
        raise NotImplementedError

    @abstractmethod
    async def get_keys_in_use(self) -> List[ApiKey]:
        """Get all keys that are currently in use."""
        raise NotImplementedError

    @abstractmethod
    async def get_key_counts(self) -> KeyCounts:
        """Get the count of keys in various states."""
        raise NotImplementedError

    @abstractmethod
    async def get_min_cool_down_until(self) -> Optional[float]:
        """Get the minimum cool_down_until value among all cooled-down keys."""
        raise NotImplementedError

    # --------------- Change Key State ---------------
    @abstractmethod
    async def save_key_state(self, state: "KeyState"):
        """Save the state of a single key."""
        raise NotImplementedError
