import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    app_logger.info("Running migration to version 10: Adding indexes to 'request_logs' table.")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_request_logs_request_time ON request_logs (request_time)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_request_logs_key_identifier ON request_logs (key_identifier)")
    await db.commit()
    app_logger.info("Indexes added to 'request_logs' table for 'request_time' and 'key_identifier'.")
