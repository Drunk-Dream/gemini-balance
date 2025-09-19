import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    """
    迁移到版本 4：创建 request_logs 表。
    """
    app_logger.info("Running migration to version 4: Creating 'request_logs' table.")
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            request_time REAL NOT NULL,
            key_identifier TEXT NOT NULL,
            auth_key_alias TEXT NOT NULL,
            model_name TEXT NOT NULL,
            is_success INTEGER NOT NULL
        )
        """
    )
    await db.commit()
    app_logger.info("'request_logs' table created or already exists.")
