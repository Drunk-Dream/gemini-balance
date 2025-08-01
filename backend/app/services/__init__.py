from app.core.config import settings

if settings.DATABASE_TYPE == "redis":
    from app.services.redis_key_manager import redis_key_manager as key_manager
elif settings.DATABASE_TYPE == "sqlite":
    from app.services.sqlite_key_manager import (  # noqa: F401
        sqlite_key_manager as key_manager,
    )
else:
    raise ImportError(f"Unsupported DATABASE_TYPE: {settings.DATABASE_TYPE}")
