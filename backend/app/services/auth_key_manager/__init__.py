from app.core.config import settings
from app.services.auth_key_manager.db_manager import AuthDBManager
from app.services.auth_key_manager.redis_manager import RedisAuthDBManager
from app.services.auth_key_manager.sqlite_manager import SQLiteAuthDBManager


def get_auth_db_manager() -> AuthDBManager:
    """
    Returns an instance of AuthDBManager based on the DATABASE_TYPE setting.
    """
    if settings.DATABASE_TYPE == "redis":
        return RedisAuthDBManager()
    elif settings.DATABASE_TYPE == "sqlite":
        return SQLiteAuthDBManager()
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")
