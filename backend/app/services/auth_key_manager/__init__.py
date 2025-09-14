from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from backend.app.core.config import get_settings
from backend.app.services.auth_key_manager.auth_service import AuthService
from backend.app.services.auth_key_manager.sqlite_manager import SQLiteAuthDBManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings


def get_auth_manager(settings: Settings = Depends(get_settings)) -> AuthService:
    """
    Returns an instance of AuthDBManager based on the DATABASE_TYPE setting.
    """
    if settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteAuthDBManager(settings)
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")

    return AuthService(db_manager)
