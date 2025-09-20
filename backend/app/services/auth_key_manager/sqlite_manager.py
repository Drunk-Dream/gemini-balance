from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import aiosqlite

from backend.app.services.auth_key_manager.db_manager import AuthDBManager
from backend.app.services.auth_key_manager.schemas import AuthKey

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class SQLiteAuthDBManager(AuthDBManager):
    """
    SQLite implementation of the AuthDBManager for authentication key storage.

    auth_keys:
        api_key TEXT PRIMARY KEY,
        alias TEXT NOT NULL UNIQUE

    """

    def __init__(self, settings: Settings):
        self.db_path = settings.SQLITE_DB

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT api_key, alias FROM auth_keys WHERE api_key = ?",
                (api_key,),
            )
            row = await cursor.fetchone()
            if row:
                return AuthKey(api_key=row[0], alias=row[1])
            return None

    async def create_key(self, auth_key: AuthKey) -> AuthKey:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO auth_keys (api_key, alias) VALUES (?, ?)",
                (auth_key.api_key, auth_key.alias),
            )
            await db.commit()
            return auth_key

    async def get_all_keys(self) -> List[AuthKey]:
        keys = []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT api_key, alias FROM auth_keys")
            rows = await cursor.fetchall()
            for row in rows:
                keys.append(AuthKey(api_key=row[0], alias=row[1]))
        return keys

    async def update_key_alias(self, api_key: str, new_alias: str) -> Optional[AuthKey]:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys=ON;")
            cursor = await db.execute(
                "UPDATE auth_keys SET alias = ? WHERE api_key = ?", (new_alias, api_key)
            )
            await db.commit()
            if cursor.rowcount > 0:
                return AuthKey(api_key=api_key, alias=new_alias)
            return None

    async def delete_key(self, api_key: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys=ON;")
            cursor = await db.execute(
                "DELETE FROM auth_keys WHERE api_key = ?", (api_key,)
            )
            await db.commit()
            return cursor.rowcount > 0
