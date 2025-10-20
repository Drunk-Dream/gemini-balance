from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import aiosqlite

from backend.app.services.request_key_manager.db_manager import DBManager
from backend.app.services.request_key_manager.schemas import (
    KeyCounts,
    KeyState,
    KeyType,
)

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class SQLiteDBManager(DBManager):
    """
    请求 keys 数据库管理器

    key_states:
        key_identifier TEXT PRIMARY KEY,
        api_key TEXT NOT NULL,
        cool_down_until REAL,
        request_fail_count INTEGER,
        cool_down_entry_count INTEGER,
        current_cool_down_seconds INTEGER,
        last_usage_time REAL,
        is_in_use INTEGER DEFAULT 0,
        is_cooled_down INTEGER DEFAULT 0

    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sqlite_db = Path(settings.SQLITE_DB)
        if not self.sqlite_db.parent.exists():
            self.sqlite_db.parent.mkdir(parents=True, exist_ok=True)

    # --------------- Key Management ---------------
    async def add_key(self, key: KeyType):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                INSERT INTO key_states (
                    key_identifier, api_key, cool_down_until, request_fail_count,
                    cool_down_entry_count, current_cool_down_seconds,
                    last_usage_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key.identifier,
                    key.full,
                    0.0,
                    0,
                    0,
                    self.settings.API_KEY_COOL_DOWN_SECONDS,
                    time.time(),
                ),
            )
            await db.commit()

    async def delete_key(self, key_identifier: str) -> Optional[str]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            async with db.execute("BEGIN IMMEDIATE") as cursor:
                await cursor.execute(
                    "SELECT api_key FROM key_states WHERE key_identifier = ?",
                    (key_identifier,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                api_key = row[0]
                await cursor.execute(
                    "DELETE FROM key_states WHERE key_identifier = ?", (key_identifier,)
                )
                await db.commit()
                return DBManager.key_to_brief(api_key)

    async def reset_key_state(self, key_identifier: str) -> Optional[str]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            async with db.execute("BEGIN IMMEDIATE") as cursor:
                await cursor.execute(
                    "SELECT api_key FROM key_states WHERE key_identifier = ?",
                    (key_identifier,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                api_key = row[0]
                await cursor.execute(
                    """
                    UPDATE key_states SET
                        cool_down_until = ?,
                        request_fail_count = ?,
                        cool_down_entry_count = ?,
                        current_cool_down_seconds = ?,
                        last_usage_time = ?,
                        is_in_use = ?,
                        is_cooled_down = ?
                    WHERE key_identifier = ?
                    """,
                    (
                        0.0,
                        0,
                        0,
                        self.settings.API_KEY_COOL_DOWN_SECONDS,
                        time.time(),
                        0,  # is_in_use 重置为 0
                        0,
                        key_identifier,
                    ),
                )
                await db.commit()
                return DBManager.key_to_brief(api_key)

    async def reset_all_key_states(self):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                UPDATE key_states SET
                    cool_down_until = ?,
                    request_fail_count = ?,
                    cool_down_entry_count = ?,
                    current_cool_down_seconds = ?,
                    last_usage_time = ?,
                    is_in_use = ?,
                    is_cooled_down = ?
                """,
                (
                    0.0,
                    0,
                    0,
                    self.settings.API_KEY_COOL_DOWN_SECONDS,
                    time.time(),
                    0,  # is_in_use 重置为 0
                    0,
                ),
            )
            await db.commit()

    # --------------- Get Key State ---------------
    def _row_to_key_state(self, row: aiosqlite.Row) -> KeyState:
        return KeyState(
            key_identifier=row["key_identifier"],
            api_key=row["api_key"],
            cool_down_until=row["cool_down_until"],
            request_fail_count=row["request_fail_count"],
            cool_down_entry_count=row["cool_down_entry_count"],
            current_cool_down_seconds=row["current_cool_down_seconds"],
            last_usage_time=row["last_usage_time"],
            is_in_use=bool(row["is_in_use"]),
            is_cooled_down=bool(row["is_cooled_down"]),
        )

    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            db.row_factory = aiosqlite.Row  # Return rows as dict-like objects
            cursor = await db.execute(
                "SELECT * FROM key_states WHERE key_identifier = ?", (key_identifier,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_key_state(row)

    async def get_all_key_states(self) -> List[KeyState]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM key_states
                ORDER BY
                    is_cooled_down ASC,
                    is_in_use DESC,
                    last_usage_time ASC
                """
            )
            rows = await cursor.fetchall()
            return [self._row_to_key_state(row) for row in rows]

    async def get_and_lock_next_available_key(self) -> Optional[KeyType]:
        """
        Atomically get the next available key and mark it as in use.
        This is done in a transaction to ensure atomicity.
        """
        async with aiosqlite.connect(self.sqlite_db) as db:
            async with db.execute("BEGIN IMMEDIATE") as cursor:
                await cursor.execute(
                    """
                    SELECT key_identifier, api_key FROM key_states
                    WHERE is_in_use = 0 AND is_cooled_down = 0
                    ORDER BY last_usage_time ASC
                    LIMIT 1
                    """
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                key_identifier = row[0]
                api_key = row[1]

                await cursor.execute(
                    "UPDATE key_states SET is_in_use = 1, last_usage_time = ? WHERE key_identifier = ?",
                    (time.time(), key_identifier),
                )
                await db.commit()

                brief_api_key = DBManager.key_to_brief(api_key)
                return KeyType(
                    identifier=key_identifier, brief=brief_api_key, full=api_key
                )

    async def get_releasable_keys(self) -> List[KeyType]:
        now = time.time()
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                "SELECT key_identifier, api_key FROM key_states WHERE is_cooled_down = 1 AND cool_down_until <= ?",
                (now,),
            )
            rows = await cursor.fetchall()
            keys = []
            for row in rows:
                key_identifier = row[0]
                api_key = row[1]
                brief_api_key = DBManager.key_to_brief(api_key)
                keys.append(
                    KeyType(
                        identifier=key_identifier, brief=brief_api_key, full=api_key
                    )
                )
            return keys

    async def get_keys_in_use(self) -> List[KeyType]:
        """Get all keys that are currently in use."""
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                "SELECT key_identifier, api_key FROM key_states WHERE is_in_use = 1"
            )
            rows = await cursor.fetchall()
            keys = []
            for row in rows:
                key_identifier = row[0]
                api_key = row[1]
                brief_api_key = DBManager.key_to_brief(api_key)
                keys.append(
                    KeyType(
                        identifier=key_identifier, brief=brief_api_key, full=api_key
                    )
                )
            return keys

    async def get_key_counts(self) -> KeyCounts:
        """Get the count of keys in various states."""
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_in_use = 1 THEN 1 ELSE 0 END) as in_use,
                    SUM(CASE WHEN is_cooled_down = 1 THEN 1 ELSE 0 END) as cooled_down,
                    SUM(CASE WHEN is_in_use = 0 AND is_cooled_down = 0 THEN 1 ELSE 0 END) as available
                FROM key_states
                """
            )
            row = await cursor.fetchone()
            if row:
                return KeyCounts(
                    total=row[0] or 0,
                    in_use=row[1] or 0,
                    cooled_down=row[2] or 0,
                    available=row[3] or 0,
                )
            return KeyCounts(total=0, in_use=0, cooled_down=0, available=0)

    async def get_min_cool_down_until(self) -> Optional[float]:
        """Get the minimum cool_down_until value among all cooled-down keys."""
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                """
                SELECT cool_down_until FROM key_states
                WHERE is_cooled_down = 1
                ORDER BY cool_down_until ASC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None

    # --------------- Change Key State ---------------
    async def save_key_state(self, state: KeyState):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                UPDATE key_states SET
                    cool_down_until = ?,
                    request_fail_count = ?,
                    cool_down_entry_count = ?,
                    current_cool_down_seconds = ?,
                    last_usage_time = ?,
                    is_in_use = ?,
                    is_cooled_down = ?
                WHERE key_identifier = ?
                """,
                (
                    state.cool_down_until,
                    state.request_fail_count,
                    state.cool_down_entry_count,
                    state.current_cool_down_seconds,
                    state.last_usage_time,
                    int(state.is_in_use),
                    int(state.is_cooled_down),
                    state.key_identifier,
                ),
            )
            await db.commit()
