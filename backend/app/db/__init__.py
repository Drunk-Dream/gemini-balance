from backend.app.core.config import Settings, settings
from backend.app.db.base_migration_manager import BaseMigrationManager
from backend.app.db.redis_migration_manager import RedisMigrationManager
from backend.app.db.sqlite_migration_manager import SQLiteMigrationManager


def get_migration_manager(settings: Settings) -> BaseMigrationManager:
    if settings.DATABASE_TYPE == "sqlite":
        return SQLiteMigrationManager(settings)
    elif settings.DATABASE_TYPE == "redis":
        return RedisMigrationManager(settings)
    else:
        raise ValueError("Unsupported database type")


migration_manager = get_migration_manager(settings)
