from typing import List, Optional

import aiosqlite
from app.api.v1beta.schemas.auth import AuthKey
from app.core.config import settings
from app.services.auth_key_manager.db_manager import AuthDBManager


class SQLiteAuthDBManager(AuthDBManager):
    """SQLite implementation of the AuthDBManager for authentication key storage."""

    def __init__(self):
        self.db_path = settings.SQLITE_DB

    async def initialize(self):
        """Initializes the database table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_keys (
                    api_key TEXT PRIMARY KEY,
                    alias TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def get_key(self, api_key: str) -> Optional[AuthKey]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT api_key, alias FROM auth_keys WHERE api_key = ?", (api_key,)
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
            cursor = await db.execute(
                "UPDATE auth_keys SET alias = ? WHERE api_key = ?", (new_alias, api_key)
            )
            await db.commit()
            if cursor.rowcount > 0:
                return AuthKey(api_key=api_key, alias=new_alias)
            return None

    async def delete_key(self, api_key: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM auth_keys WHERE api_key = ?", (api_key,)
            )
            await db.commit()
            return cursor.rowcount > 0
