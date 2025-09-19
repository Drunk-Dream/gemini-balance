import importlib.util
import re
from pathlib import Path
from typing import Awaitable, Callable, Dict

import aiosqlite

from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.db.base_migration_manager import BaseMigrationManager

# 迁移函数字典，键为版本号，值为对应的迁移函数
MIGRATIONS: Dict[int, Callable[[aiosqlite.Connection], Awaitable[None]]] = {}
CURRENT_DB_VERSION = 0  # 初始设置为 0，将在加载迁移时更新


def _load_migrations():
    """
    动态加载 'migrations/versions' 目录下的所有迁移脚本。
    """
    global CURRENT_DB_VERSION
    migrations_dir = Path(__file__).parent / "migrations" / "versions"
    if not migrations_dir.exists():
        app_logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    for migration_file in sorted(migrations_dir.glob("v*.py")):
        if migration_file.name == "__init__.py":
            continue

        match = re.match(r"v(\d+)_.*\.py", migration_file.name)
        if not match:
            app_logger.warning(f"Skipping non-migration file: {migration_file.name}")
            continue

        version = int(match.group(1))
        module_name = f"migrations.versions.{migration_file.stem}"

        spec = importlib.util.spec_from_file_location(module_name, migration_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "upgrade") and callable(module.upgrade):
                MIGRATIONS[version] = module.upgrade  # type: ignore
                CURRENT_DB_VERSION = max(CURRENT_DB_VERSION, version)
                app_logger.debug(f"Loaded migration v{version} from {migration_file.name}")
            else:
                app_logger.warning(
                    f"Migration file {migration_file.name} does not contain an 'upgrade' function."
                )
        else:
            app_logger.error(f"Failed to load module spec for {migration_file.name}")

    app_logger.info(f"Loaded {len(MIGRATIONS)} migrations. Current DB version set to: {CURRENT_DB_VERSION}")


# 在模块加载时执行迁移加载
_load_migrations()


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
                # 确保按版本号顺序执行迁移
                for version in sorted(MIGRATIONS.keys()):
                    if version > current_version:
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
