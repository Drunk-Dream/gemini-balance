import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    app_logger.info("Running migration to version 7: Adding 'prompt_tokens', 'completion_tokens', 'total_tokens' to 'request_logs' table.")
    await db.execute("ALTER TABLE request_logs ADD COLUMN prompt_tokens INTEGER")
    await db.execute("ALTER TABLE request_logs ADD COLUMN completion_tokens INTEGER")
    await db.execute("ALTER TABLE request_logs ADD COLUMN total_tokens INTEGER")
    await db.commit()
    app_logger.info("'prompt_tokens', 'completion_tokens', 'total_tokens' added to 'request_logs' table.")
