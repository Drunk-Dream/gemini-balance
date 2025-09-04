from pathlib import Path
from typing import Awaitable, Callable, Dict

import aiosqlite

from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.db.base_migration_manager import BaseMigrationManager

# 定义数据库的当前版本
CURRENT_DB_VERSION = 3

# 迁移函数字典，键为版本号，值为对应的迁移函数
MIGRATIONS: Dict[int, Callable[[aiosqlite.Connection], Awaitable[None]]] = {}


async def _migration_v1(db: aiosqlite.Connection):
    """
    迁移到版本 1：创建 key_states 表。
    """
    app_logger.info("Running migration to version 1: Creating 'key_states' table.")
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS key_states (
            key_identifier TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            cool_down_until REAL,
            request_fail_count INTEGER,
            cool_down_entry_count INTEGER,
            current_cool_down_seconds INTEGER,
            usage_today TEXT,
            last_usage_date TEXT,
            last_usage_time REAL,
            is_in_use INTEGER DEFAULT 0,
            is_cooled_down INTEGER DEFAULT 0
        )
        """
    )
    await db.commit()
    app_logger.info("'key_states' table created or already exists.")


MIGRATIONS[1] = _migration_v1


async def _migration_v2(db: aiosqlite.Connection):
    """
    迁移到版本 2：创建 auth_keys 表。
    """
    app_logger.info("Running migration to version 2: Creating 'auth_keys' table.")
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_keys (
            api_key TEXT PRIMARY KEY,
            alias TEXT NOT NULL,
            call_count INTEGER DEFAULT 0
        )
        """
    )
    await db.commit()
    app_logger.info("'auth_keys' table created or already exists.")


MIGRATIONS[2] = _migration_v2


async def _migration_v3(db: aiosqlite.Connection):
    """
    迁移到版本 3：从 key_states 表中移除 last_usage_date 列。
    """
    app_logger.info("Running migration to version 3: Removing 'last_usage_date' from 'key_states' table.")

    # 1. 将旧表重命名
    await db.execute("ALTER TABLE key_states RENAME TO old_key_states")
    app_logger.info("Renamed 'key_states' to 'old_key_states'.")

    # 2. 创建新表，不包含 last_usage_date
    await db.execute(
        """
        CREATE TABLE key_states (
            key_identifier TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            cool_down_until REAL,
            request_fail_count INTEGER,
            cool_down_entry_count INTEGER,
            current_cool_down_seconds INTEGER,
            usage_today TEXT,
            last_usage_time REAL,
            is_in_use INTEGER DEFAULT 0,
            is_cooled_down INTEGER DEFAULT 0
        )
        """
    )
    app_logger.info("Created new 'key_states' table without 'last_usage_date'.")

    # 3. 将数据从旧表复制到新表
    await db.execute(
        """
        INSERT INTO key_states (
            key_identifier, api_key, cool_down_until, request_fail_count,
            cool_down_entry_count, current_cool_down_seconds, usage_today,
            last_usage_time, is_in_use, is_cooled_down
        )
        SELECT
            key_identifier, api_key, cool_down_until, request_fail_count,
            cool_down_entry_count, current_cool_down_seconds, usage_today,
            last_usage_time, is_in_use, is_cooled_down
        FROM old_key_states
        """
    )
    app_logger.info("Copied data from 'old_key_states' to new 'key_states'.")

    # 4. 删除旧表
    await db.execute("DROP TABLE old_key_states")
    app_logger.info("Dropped 'old_key_states' table.")
    await db.commit()


MIGRATIONS[3] = _migration_v3


class SQLiteMigrationManager(BaseMigrationManager):
    def __init__(self, settings: Settings):
        self.db_path = Path(settings.SQLITE_DB)

    async def get_db_version(self) -> int:
        """获取数据库的当前版本号。"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("PRAGMA user_version")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def set_db_version(self, version: int):
        """设置数据库的版本号。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"PRAGMA user_version = {version}")
            await db.commit()

    async def run_migrations(self):
        """
        运行所有必要的数据库迁移。
        """
        # 确保数据库文件所在的目录存在
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            app_logger.info(f"Created database directory: {self.db_path.parent}")

        async with aiosqlite.connect(self.db_path) as db:
            current_version = await self.get_db_version()
            app_logger.info(f"Current database version: {current_version}")

            if current_version < CURRENT_DB_VERSION:
                app_logger.info(
                    f"Starting database migration from version {current_version} to {CURRENT_DB_VERSION}."
                )
                for version in range(current_version + 1, CURRENT_DB_VERSION + 1):
                    migration_func = MIGRATIONS.get(version)
                    if migration_func:
                        app_logger.info(f"Applying migration for version {version}...")
                        await migration_func(db)
                        await self.set_db_version(version)
                        app_logger.info(f"Migration to version {version} completed.")
                    else:
                        app_logger.error(
                            f"No migration function found for version {version}. This indicates a configuration error."
                        )
                        raise RuntimeError(f"Missing migration for version {version}")
            else:
                app_logger.info("Database is already up to date.")
