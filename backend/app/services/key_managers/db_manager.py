import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class KeyState(BaseModel):
    key_identifier: str
    api_key: str  # 新增字段
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    usage_today: Dict[str, int] = Field(default_factory=dict)
    last_usage_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )
    last_usage_time: float = Field(default_factory=lambda: time.time())


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
    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        """Get the raw API key from its identifier."""
        pass

    @abstractmethod
    async def save_key_state(self, key_identifier: str, state: "KeyState"):
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
    async def release_key_from_use(self, key_identifier: str):
        """Release a key from being in use, setting its is_in_use flag to 0."""
        pass

    @abstractmethod
    async def add_key(self, key_identifier: str, api_key: str):
        """Add a new API key to the database."""
        pass

    @abstractmethod
    async def delete_key(self, key_identifier: str):
        """Delete an API key from the database."""
        pass

    @abstractmethod
    async def reset_key_state(self, key_identifier: str):
        """Reset the state of a specific API key."""
        pass

    @abstractmethod
    async def reset_all_key_states(self):
        """Reset the state of all API keys."""
        pass
