from typing import Any, Awaitable, Callable, Dict

import redis.asyncio as redis

from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.db.base_migration_manager import BaseMigrationManager

# 定义数据库的当前版本
CURRENT_DB_VERSION = 2

# 迁移函数字典，键为版本号，值为对应的迁移函数
MIGRATIONS: Dict[int, Callable[[Any], Awaitable[None]]] = {}


async def _migration_v1(db: redis.Redis):
    """
    迁移到版本 1：Redis 无需模式迁移，仅记录。
    """
    app_logger.info(
        "Running Redis migration to version 1: No schema changes needed for key_states."
    )


MIGRATIONS[1] = _migration_v1


async def _migration_v2(db: redis.Redis):
    """
    迁移到版本 2：Redis 无需模式迁移，仅记录。
    """
    app_logger.info(
        "Running Redis migration to version 2: No schema changes needed for auth_keys."
    )


MIGRATIONS[2] = _migration_v2


async def _migration_v3(db: redis.Redis):
    """
    迁移到版本 3：Redis 无需模式迁移，仅记录。
    """
    app_logger.info(
        "Running Redis migration to version 3: No schema changes needed for auth_keys."
    )


MIGRATIONS[3] = _migration_v3


class RedisMigrationManager(BaseMigrationManager):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
        )
        self.DB_VERSION_KEY = "db_version"

    async def get_db_version(self) -> int:
        """获取 Redis 数据库的当前版本号。"""
        version = await self._redis.get(self.DB_VERSION_KEY)  # type: ignore
        return int(version) if version else 0

    async def set_db_version(self, version: int):
        """设置 Redis 数据库的版本号。"""
        await self._redis.set(self.DB_VERSION_KEY, str(version))  # type: ignore
        app_logger.info(f"Set Redis database version to {version}.")

    async def run_migrations(self):
        """
        运行所有必要的 Redis 数据库迁移。
        """
        current_version = await self.get_db_version()
        app_logger.info(f"Current Redis database version: {current_version}")

        if current_version < CURRENT_DB_VERSION:
            app_logger.info(
                f"Starting Redis database migration from version {current_version} to {CURRENT_DB_VERSION}."
            )
            for version in range(current_version + 1, CURRENT_DB_VERSION + 1):
                migration_func = MIGRATIONS.get(version)
                if migration_func:
                    app_logger.info(
                        f"Applying Redis migration for version {version}..."
                    )
                    await migration_func(self._redis)
                    await self.set_db_version(version)
                    app_logger.info(f"Redis migration to version {version} completed.")
                else:
                    app_logger.error(
                        f"No Redis migration function found for version {version}. This indicates a configuration error."
                    )
                    raise RuntimeError(f"Missing Redis migration for version {version}")
        else:
            app_logger.info("Redis database is already up to date.")
