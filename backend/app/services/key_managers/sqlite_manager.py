import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Set

from app.core.config import Settings
from app.core.logging import app_logger
from app.services.key_managers.db_manager import DBManager, KeyState


class SQLiteDBManager(DBManager):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sqlite_db = Path(settings.SQLITE_DB)
        if not self.sqlite_db.parent.exists():
            self.sqlite_db.parent.mkdir(parents=True, exist_ok=True)

    async def _execute_query(self, query: str, params: tuple = ()):
        return await asyncio.to_thread(self._sync_execute_query, query, params)

    def _sync_execute_query(self, query: str, params: tuple = ()):
        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        finally:
            conn.close()

    async def initialize(self):
        await self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS key_states (
                key_identifier TEXT PRIMARY KEY,
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

    async def get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        rows = await self._execute_query(
            "SELECT * FROM key_states WHERE key_identifier = ?", (key_identifier,)
        )
        if not rows:
            return None
        return self._row_to_key_state(rows[0])

    async def save_key_state(self, key_identifier: str, state: KeyState):
        await self._execute_query(
            """
            UPDATE key_states SET
                cool_down_until = ?,
                request_fail_count = ?,
                cool_down_entry_count = ?,
                current_cool_down_seconds = ?,
                usage_today = ?,
                last_usage_date = ?,
                last_usage_time = ?
            WHERE key_identifier = ?
            """,
            (
                state.cool_down_until,
                state.request_fail_count,
                state.cool_down_entry_count,
                state.current_cool_down_seconds,
                json.dumps(state.usage_today),
                state.last_usage_date,
                state.last_usage_time,
                key_identifier,
            ),
        )

    async def get_all_key_states(self) -> List[KeyState]:
        rows = await self._execute_query("SELECT * FROM key_states")
        return [self._row_to_key_state(row) for row in rows]

    async def get_next_available_key(self) -> Optional[str]:
        async with asyncio.Lock():  # Use a lock to prevent race conditions
            rows = await self._execute_query(
                """
                SELECT key_identifier FROM key_states
                WHERE is_in_use = 0 AND is_cooled_down = 0
                ORDER BY last_usage_time ASC
                LIMIT 1
                """
            )
            if not rows:
                return None
            key_identifier = rows[0][0]
            await self._execute_query(
                "UPDATE key_states SET is_in_use = 1, last_usage_time = ? WHERE key_identifier = ?",
                (time.time(), key_identifier),
            )
            return key_identifier

    async def move_to_cooldown(self, key_identifier: str, cool_down_until: float):
        await self._execute_query(
            "UPDATE key_states SET is_cooled_down = 1, cool_down_until = ?, is_in_use = 0 WHERE key_identifier = ?",
            (cool_down_until, key_identifier),
        )

    async def get_releasable_keys(self) -> List[str]:
        now = time.time()
        rows = await self._execute_query(
            "SELECT key_identifier FROM key_states WHERE is_cooled_down = 1 AND cool_down_until <= ?",
            (now,),
        )
        return [row[0] for row in rows]

    async def reactivate_key(self, key_identifier: str):
        await self._execute_query(
            "UPDATE key_states SET is_cooled_down = 0, is_in_use = 0, request_fail_count = 0 WHERE key_identifier = ?",
            (key_identifier,),
        )

    async def sync_keys(self, config_keys: Set[str]):
        db_keys_raw = await self._execute_query("SELECT key_identifier FROM key_states")
        db_keys = {row[0] for row in db_keys_raw}

        for key_identifier in config_keys - db_keys:
            await self._execute_query(
                """
                INSERT INTO key_states (
                    key_identifier, cool_down_until, request_fail_count,
                    cool_down_entry_count, current_cool_down_seconds,
                    usage_today, last_usage_date, last_usage_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key_identifier,
                    0.0,
                    0,
                    0,
                    self.settings.API_KEY_COOL_DOWN_SECONDS,
                    "{}",
                    time.strftime("%Y-%m-%d"),
                    time.time(),
                ),
            )
            app_logger.info(f"Added new API key '{key_identifier}' to DB.")

        for key_identifier in db_keys - config_keys:
            await self._execute_query(
                "DELETE FROM key_states WHERE key_identifier = ?", (key_identifier,)
            )
            app_logger.info(f"Removed API key '{key_identifier}' from DB.")

    def _row_to_key_state(self, row: tuple) -> KeyState:
        return KeyState(
            key_identifier=row[0],
            cool_down_until=row[1],
            request_fail_count=row[2],
            cool_down_entry_count=row[3],
            current_cool_down_seconds=row[4],
            usage_today=json.loads(row[5]),
            last_usage_date=row[6],
            last_usage_time=row[7],
        )
