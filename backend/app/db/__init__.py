"""
数据库迁移模块。

该模块负责根据应用配置初始化正确的数据库迁移管理器，并在应用启动时自动运行数据库迁移。
它支持可插拔的数据库类型，目前主要实现 SQLite 数据库的迁移管理。

工作原理：
1.  `get_migration_manager` 函数根据 `settings.DATABASE_TYPE` 返回相应的迁移管理器实例。
    目前支持 "sqlite" 类型，未来可扩展支持其他数据库。
2.  `migration_manager` 实例在模块加载时被创建，确保在应用的其他部分需要时即可使用。
3.  `SQLiteMigrationManager` 会动态加载 `backend/app/db/migrations/versions/` 目录下的所有迁移脚本。
    每个迁移脚本文件应命名为 `v<版本号>_<描述>.py` (例如 `v1_create_initial_tables.py`)，
    并包含一个名为 `upgrade` 的异步函数，该函数接受一个 `aiosqlite.Connection` 对象作为参数，
    并执行该版本对应的数据库升级逻辑。
4.  `SQLiteMigrationManager` 会根据已加载的迁移脚本自动确定当前的数据库最新版本。
5.  在 `run_migrations` 方法被调用时，它会检查数据库的当前版本，并按顺序执行所有尚未应用的迁移。

如何进行数据库版本更新：
1.  在 `backend/app/db/migrations/versions/` 目录下创建一个新的 Python 文件。
    文件命名应遵循 `v<下一个版本号>_<简要描述>.py` 的格式。
    例如，如果当前最高版本是 v4，则新文件应命名为 `v5_add_new_column_to_table.py`。
2.  在新文件中定义一个异步函数 `upgrade(db: aiosqlite.Connection)`，并在其中编写该版本对应的 SQL 迁移逻辑。
    例如：
    ```python
    import aiosqlite
    from backend.app.core.logging import app_logger

    async def upgrade(db: aiosqlite.Connection):
        app_logger.info("Running migration to version 5: Adding 'new_column' to 'some_table'.")
        await db.execute("ALTER TABLE some_table ADD COLUMN new_column TEXT DEFAULT 'default_value'")
        await db.commit()
        app_logger.info("'new_column' added to 'some_table'.")
    ```
3.  无需手动更新 `CURRENT_DB_VERSION` 或 `MIGRATIONS` 字典，`SQLiteMigrationManager` 会在运行时自动检测并加载新的迁移文件。
4.  确保在应用启动时调用 `migration_manager.run_migrations()` 方法，以执行新的迁移。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.db.base_migration_manager import BaseMigrationManager
from backend.app.db.sqlite_migration_manager import SQLiteMigrationManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings


def get_migration_manager(settings: Settings) -> BaseMigrationManager:
    if settings.DATABASE_TYPE == "sqlite":
        return SQLiteMigrationManager(settings)
    else:
        raise ValueError("Unsupported database type")
