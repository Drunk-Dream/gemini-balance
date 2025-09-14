from datetime import datetime
from typing import List, Optional

import aiosqlite

from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.schemas import RequestLog


class SQLiteRequestLogManager(RequestLogDBManager):
    """
    使用 aiosqlite 实现的请求日志数据库管理器。
    """

    def __init__(self, settings: Settings):
        self.db_path = settings.SQLITE_DB

    async def record_request_log(self, log: RequestLog) -> None:
        """
        记录一个请求日志条目到 SQLite 数据库。
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO request_logs (request_id, request_time, key_identifier, auth_key_alias, model_name, is_success)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log.request_id,
                    log.request_time.timestamp(),  # 存储为 Unix 时间戳
                    log.key_identifier,
                    log.auth_key_alias,
                    log.model_name,
                    int(log.is_success),  # 存储布尔值为整数 0 或 1
                ),
            )
            await db.commit()
            app_logger.debug(f"Request log recorded: {log.request_id}")

    async def get_request_logs(
        self,
        request_time_start: Optional[datetime] = None,
        request_time_end: Optional[datetime] = None,
        key_identifier: Optional[str] = None,
        auth_key_alias: Optional[str] = None,
        model_name: Optional[str] = None,
        is_success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RequestLog]:
        """
        根据过滤条件从 SQLite 数据库获取请求日志条目。
        """
        query = "SELECT * FROM request_logs WHERE 1=1"
        params = []

        if request_time_start:
            query += " AND request_time >= ?"
            params.append(request_time_start.timestamp())
        if request_time_end:
            query += " AND request_time <= ?"
            params.append(request_time_end.timestamp())
        if key_identifier:
            query += " AND key_identifier = ?"
            params.append(key_identifier)
        if auth_key_alias:
            query += " AND auth_key_alias = ?"
            params.append(auth_key_alias)
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        if is_success is not None:
            query += " AND is_success = ?"
            params.append(int(is_success))

        query += " ORDER BY request_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row  # 设置行工厂，以便通过名称访问列
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [
                RequestLog(
                    id=row["id"],
                    request_id=row["request_id"],
                    request_time=datetime.fromtimestamp(row["request_time"]),
                    key_identifier=row["key_identifier"],
                    auth_key_alias=row["auth_key_alias"],
                    model_name=row["model_name"],
                    is_success=bool(row["is_success"]),
                )
                for row in rows
            ]
