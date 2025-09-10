from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.auth_key_manager.redis_manager import RedisAuthDBManager
from backend.app.services.auth_key_manager.sqlite_manager import SQLiteAuthDBManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.auth_key_manager.db_manager import AuthDBManager


def get_auth_db_manager(settings: Settings) -> AuthDBManager:
    """
    Returns an instance of AuthDBManager based on the DATABASE_TYPE setting.
    """
    if settings.DATABASE_TYPE == "redis":
        return RedisAuthDBManager(settings)
    elif settings.DATABASE_TYPE == "sqlite":
        return SQLiteAuthDBManager(settings)
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")
