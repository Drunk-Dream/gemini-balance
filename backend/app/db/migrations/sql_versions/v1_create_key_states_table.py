import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
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
