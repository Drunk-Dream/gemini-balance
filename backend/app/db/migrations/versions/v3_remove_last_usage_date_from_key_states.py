import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    """
    迁移到版本 3：从 key_states 表中移除 last_usage_date 列。
    """
    app_logger.info(
        "Running migration to version 3: Removing 'last_usage_date' from 'key_states' table."
    )

    # 1. 将旧表重命名
    await db.execute("ALTER TABLE key_states RENAME TO old_key_states")
    app_logger.info("Renamed 'key_states' to 'old_key_states'.")

    # 2. 创建新表，不包含 last_usage_date
    await db.execute(
        """
        CREATE TABLE key_states (
            key_identifier TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            cool_down_until REAL,
            request_fail_count INTEGER,
            cool_down_entry_count INTEGER,
            current_cool_down_seconds INTEGER,
            usage_today TEXT,
            last_usage_time REAL,
            is_in_use INTEGER DEFAULT 0,
            is_cooled_down INTEGER DEFAULT 0
        )
        """
    )
    app_logger.info("Created new 'key_states' table without 'last_usage_date'.")

    # 3. 将数据从旧表复制到新表
    await db.execute(
        """
        INSERT INTO key_states (
            key_identifier, api_key, cool_down_until, request_fail_count,
            cool_down_entry_count, current_cool_down_seconds, usage_today,
            last_usage_time, is_in_use, is_cooled_down
        )
        SELECT
            key_identifier, api_key, cool_down_until, request_fail_count,
            cool_down_entry_count, current_cool_down_seconds, usage_today,
            last_usage_time, is_in_use, is_cooled_down
        FROM old_key_states
        """
    )
    app_logger.info("Copied data from 'old_key_states' to new 'key_states'.")

    # 4. 删除旧表
    await db.execute("DROP TABLE old_key_states")
    app_logger.info("Dropped 'old_key_states' table.")
    await db.commit()
