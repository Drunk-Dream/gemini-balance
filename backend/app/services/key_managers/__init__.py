from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from backend.app.core.config import get_settings
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.key_managers.db_manager import DBManager


def get_key_db_manager(
    settings: Settings = Depends(get_settings),
) -> DBManager:
    db_manager: DBManager
    if settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteDBManager(settings)
    else:
        raise ValueError(f"Unsupported key manager type: {settings.DATABASE_TYPE}")
    return db_manager
