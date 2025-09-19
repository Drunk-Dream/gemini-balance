import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
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
