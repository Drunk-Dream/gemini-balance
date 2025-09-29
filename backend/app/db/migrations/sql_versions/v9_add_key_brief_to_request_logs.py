import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    app_logger.info(
        "Running migration to version 9: Adding 'key_brief' to 'request_logs' table."
    )
    await db.execute("ALTER TABLE request_logs ADD COLUMN key_brief TEXT")
    await db.commit()
    app_logger.info("Migration to version 9 completed successfully.")
