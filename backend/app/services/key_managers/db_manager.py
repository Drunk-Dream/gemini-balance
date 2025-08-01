from abc import ABC, abstractmethod
from typing import List, Optional, Set

from app.services.key_manager import KeyState


class DBManager(ABC):
    """
    Abstract class for database operations for the key manager.
    """

    @abstractmethod
    async def initialize(self):
        """Initialize the database connection and tables."""
        pass

    @abstractmethod
    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        """Get the state of a single key."""
        pass

    @abstractmethod
    async def save_key_state(self, key_identifier: str, state: KeyState):
        """Save the state of a single key."""
        pass

    @abstractmethod
    async def get_all_key_states(self) -> List[KeyState]:
        """Get the states of all keys."""
        pass

    @abstractmethod
    async def get_next_available_key(self) -> Optional[str]:
        """Get the next available key identifier."""
        pass

    @abstractmethod
    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        """Move a key to the cooldown queue."""
        pass

    @abstractmethod
    async def get_releasable_keys(self) -> List[str]:
        """Get all keys that have finished their cooldown."""
        pass

    @abstractmethod
    async def reactivate_key(self, key_identifier: str):
        """Reactivate a key, moving it back to the available queue."""
        pass

    @abstractmethod
    async def sync_keys(self, config_keys: Set[str]):
        """Synchronize the keys in the database with the keys from the config."""
        pass
