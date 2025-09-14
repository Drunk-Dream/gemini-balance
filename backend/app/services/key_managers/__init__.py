from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from backend.app.core.config import get_settings
from backend.app.services.key_managers.key_state_manager import KeyStateManager
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings


def get_key_manager(settings: Settings = Depends(get_settings)) -> KeyStateManager:
    if settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteDBManager(settings)
    else:
        raise ValueError(f"Unsupported key manager type: {settings.DATABASE_TYPE}")
    return KeyStateManager(settings, db_manager)
