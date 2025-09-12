from __future__ import annotations

import asyncio  # 导入 asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import aiosqlite
import pytz  # type: ignore

from backend.app.core.logging import app_logger
from backend.app.services.key_managers.db_manager import DBManager, KeyState

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class SQLiteDBManager(DBManager):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sqlite_db = Path(settings.SQLITE_DB)
        if not self.sqlite_db.parent.exists():
            self.sqlite_db.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()  # 初始化异步锁

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

    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                "SELECT api_key FROM key_states WHERE key_identifier = ?",
                (key_identifier,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def save_key_state(self, key_identifier: str, state: KeyState):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                UPDATE key_states SET
                    api_key = ?,
                    cool_down_until = ?,
                    request_fail_count = ?,
                    cool_down_entry_count = ?,
                    current_cool_down_seconds = ?,
                    usage_today = ?,
                    last_usage_time = ?
                WHERE key_identifier = ?
                """,
                (
                    state.api_key,
                    state.cool_down_until,
                    state.request_fail_count,
                    state.cool_down_entry_count,
                    state.current_cool_down_seconds,
                    json.dumps(state.usage_today),
                    state.last_usage_time,
                    key_identifier,
                ),
            )
            await db.commit()

    async def get_all_key_states(self) -> List[KeyState]:
        async with aiosqlite.connect(self.sqlite_db) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM key_states")
            rows = await cursor.fetchall()
            return [self._row_to_key_state(row) for row in rows]

    async def get_next_available_key(self) -> Optional[str]:
        async with self._lock:  # 使用异步锁确保并发安全
            async with aiosqlite.connect(self.sqlite_db) as db:
                try:
                    cursor = await db.execute(
                        """
                        SELECT key_identifier FROM key_states
                        WHERE is_in_use = 0 AND is_cooled_down = 0
                        ORDER BY last_usage_time ASC
                        LIMIT 1
                        """
                    )
                    row = await cursor.fetchone()
                    if not row:
                        return None
                    key_identifier = row[0]
                    return key_identifier
                except Exception as e:
                    app_logger.error(f"Error getting next available key: {e}")
                    await db.rollback()
                    return None

    async def move_to_use(self, key_identifier: str):
        """Mark a key as in use and update its last usage time in SQLite."""
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                "UPDATE key_states SET is_in_use = 1, last_usage_time = ? WHERE key_identifier = ?",
                (time.time(), key_identifier),
            )
            await db.commit()

    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                "UPDATE key_states SET is_cooled_down = 1, cool_down_until = ?, is_in_use = 0 WHERE key_identifier = ?",
                (cool_down_until, key_identifier),
            )
            await db.commit()

    async def get_releasable_keys(self) -> List[str]:
        now = time.time()
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                "SELECT key_identifier FROM key_states WHERE is_cooled_down = 1 AND cool_down_until <= ?",
                (now,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_keys_in_use(self) -> List[str]:
        """Get all keys that are currently in use."""
        async with aiosqlite.connect(self.sqlite_db) as db:
            cursor = await db.execute(
                "SELECT key_identifier FROM key_states WHERE is_in_use = 1"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def reactivate_key(self, key_identifier: str):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                "UPDATE key_states SET is_cooled_down = 0, is_in_use = 0, request_fail_count = 0 WHERE key_identifier = ?",
                (key_identifier,),
            )
            await db.commit()

    async def add_key(self, key_identifier: str, api_key: str):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                INSERT INTO key_states (
                    key_identifier, api_key, cool_down_until, request_fail_count,
                    cool_down_entry_count, current_cool_down_seconds,
                    usage_today, last_usage_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key_identifier,
                    api_key,
                    0.0,
                    0,
                    0,
                    self.settings.API_KEY_COOL_DOWN_SECONDS,
                    "{}",
                    time.time(),
                ),
            )
            await db.commit()
            app_logger.info(f"Added new API key '{key_identifier}' to DB.")

    async def delete_key(self, key_identifier: str):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                "DELETE FROM key_states WHERE key_identifier = ?", (key_identifier,)
            )
            await db.commit()
            app_logger.info(f"Removed API key '{key_identifier}' from DB.")

    async def reset_key_state(self, key_identifier: str):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                UPDATE key_states SET
                    cool_down_until = ?,
                    request_fail_count = ?,
                    cool_down_entry_count = ?,
                    current_cool_down_seconds = ?,
                    usage_today = ?,
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
                    "{}",
                    time.time(),
                    0,  # is_in_use 重置为 0
                    0,
                    key_identifier,
                ),
            )
            await db.commit()
            app_logger.info(f"Reset state for API key '{key_identifier}' in DB.")

    async def reset_all_key_states(self):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                """
                UPDATE key_states SET
                    cool_down_until = ?,
                    request_fail_count = ?,
                    cool_down_entry_count = ?,
                    current_cool_down_seconds = ?,
                    usage_today = ?,
                    last_usage_time = ?,
                    is_in_use = ?,
                    is_cooled_down = ?
                """,
                (
                    0.0,
                    0,
                    0,
                    self.settings.API_KEY_COOL_DOWN_SECONDS,
                    "{}",
                    time.time(),
                    0,  # is_in_use 重置为 0
                    0,
                ),
            )
            await db.commit()
            app_logger.info("Reset state for all API keys in DB.")

    async def release_key_from_use(self, key_identifier: str):
        async with aiosqlite.connect(self.sqlite_db) as db:
            await db.execute(
                "UPDATE key_states SET is_in_use = 0 WHERE key_identifier = ?",
                (key_identifier,),
            )
            await db.commit()

    def _row_to_key_state(self, row: aiosqlite.Row) -> KeyState:
        eastern_tz = pytz.timezone("America/New_York")
        last_usage_date = datetime.fromtimestamp(
            row["last_usage_time"], tz=eastern_tz
        ).strftime("%Y-%m-%d")
        return KeyState(
            key_identifier=row["key_identifier"],
            api_key=row["api_key"],
            cool_down_until=row["cool_down_until"],
            request_fail_count=row["request_fail_count"],
            cool_down_entry_count=row["cool_down_entry_count"],
            current_cool_down_seconds=row["current_cool_down_seconds"],
            usage_today=json.loads(row["usage_today"]),
            last_usage_date=last_usage_date,
            last_usage_time=row["last_usage_time"],
            is_in_use=bool(row["is_in_use"]),
        )
