from backend.app.core.config import Settings
from backend.app.services.key_managers.key_state_manager import KeyStateManager
from backend.app.services.key_managers.redis_manager import RedisDBManager
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager


def get_key_manager(settings: Settings) -> KeyStateManager:
    if settings.DATABASE_TYPE == "redis":
        db_manager = RedisDBManager(settings)
    elif settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteDBManager(settings)
    else:
        raise ValueError(f"Unsupported key manager type: {settings.DATABASE_TYPE}")
    return KeyStateManager(settings, db_manager)
