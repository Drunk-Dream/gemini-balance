import aiosqlite

from backend.app.core.logging import app_logger


async def upgrade(db: aiosqlite.Connection):
    """
    Applies the database schema changes for version 6.

    - auth_keys:
        - Adds a UNIQUE constraint to the 'alias' column.
        - Removes the 'call_count' column.
    - request_logs:
        - Adds a foreign key constraint to 'key_identifier' referencing 'key_states'.
        - Adds a foreign key constraint to 'auth_key_alias' referencing 'auth_keys'.
    """
    app_logger.info("Running migration to version 6: Updating table constraints.")

    # Turn on foreign key support
    await db.execute("PRAGMA foreign_keys=ON;")

    # --- auth_keys table migration ---
    app_logger.info("Migrating 'auth_keys' table...")
    # Create a new table with the desired schema
    await db.execute(
        """
        CREATE TABLE auth_keys_new (
            api_key TEXT PRIMARY KEY,
            alias TEXT NOT NULL UNIQUE
        );
        """
    )
    # Copy data from the old table to the new table
    await db.execute(
        """
        INSERT INTO auth_keys_new (api_key, alias)
        SELECT api_key, alias FROM auth_keys;
        """
    )
    # Drop the old table
    await db.execute("DROP TABLE auth_keys;")
    # Rename the new table to the original name
    await db.execute("ALTER TABLE auth_keys_new RENAME TO auth_keys;")
    app_logger.info("'auth_keys' table migrated successfully.")

    # --- request_logs table migration ---
    app_logger.info("Migrating 'request_logs' table...")
    # Create a new table with foreign key constraints
    await db.execute(
        """
        CREATE TABLE request_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            request_time REAL NOT NULL,
            key_identifier TEXT NOT NULL,
            auth_key_alias TEXT NOT NULL,
            model_name TEXT NOT NULL,
            is_success INTEGER NOT NULL,
            FOREIGN KEY (key_identifier) REFERENCES key_states(key_identifier) ON DELETE CASCADE,
            FOREIGN KEY (auth_key_alias) REFERENCES auth_keys(alias) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """
    )
    # Copy data from the old table to the new table
    await db.execute(
        """
        INSERT INTO request_logs_new (id, request_id, request_time, key_identifier, auth_key_alias, model_name, is_success)
        SELECT id, request_id, request_time, key_identifier, auth_key_alias, model_name, is_success FROM request_logs;
        """
    )
    # Drop the old table
    await db.execute("DROP TABLE request_logs;")
    # Rename the new table to the original name
    await db.execute("ALTER TABLE request_logs_new RENAME TO request_logs;")
    app_logger.info("'request_logs' table migrated successfully.")

    await db.commit()
    app_logger.info("Migration to version 6 completed successfully.")
