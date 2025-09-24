import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    app_logger.info("Running migration to version 8: Adding 'error_type' to 'request_logs' table.")
    await db.execute("ALTER TABLE request_logs ADD COLUMN error_type TEXT")
    await db.commit()
    app_logger.info("Migration to version 8 completed successfully.")
