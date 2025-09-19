import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    app_logger.info(
        "Running migration to version 5: Removing 'usage_today' from 'key_states' table."
    )
    await db.execute("ALTER TABLE key_states DROP COLUMN usage_today")
    await db.commit()
    app_logger.info("'usage_today' column removed from 'key_states' table.")
