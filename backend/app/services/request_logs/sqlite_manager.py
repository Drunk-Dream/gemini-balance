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

    def _build_filter_query(
        self,
        request_time_start: Optional[datetime] = None,
        request_time_end: Optional[datetime] = None,
        key_identifier: Optional[str] = None,
        auth_key_alias: Optional[str] = None,
        model_name: Optional[str] = None,
        is_success: Optional[bool] = None,
    ) -> tuple[str, list]:
        """
        构建 WHERE 子句和参数列表。
        """
        query_parts = ["WHERE 1=1"]
        params = []

        if request_time_start:
            query_parts.append("AND request_time >= ?")
            params.append(request_time_start.timestamp())
        if request_time_end:
            query_parts.append("AND request_time <= ?")
            params.append(request_time_end.timestamp())
        if key_identifier:
            query_parts.append("AND key_identifier = ?")
            params.append(key_identifier)
        if auth_key_alias:
            query_parts.append("AND auth_key_alias = ?")
            params.append(auth_key_alias)
        if model_name:
            query_parts.append("AND model_name = ?")
            params.append(model_name)
        if is_success is not None:
            query_parts.append("AND is_success = ?")
            params.append(int(is_success))

        return " ".join(query_parts), params

    async def get_request_logs_with_count(
        self,
        request_time_start: Optional[datetime] = None,
        request_time_end: Optional[datetime] = None,
        key_identifier: Optional[str] = None,
        auth_key_alias: Optional[str] = None,
        model_name: Optional[str] = None,
        is_success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[RequestLog], int]:
        """
        根据过滤条件从 SQLite 数据库获取请求日志条目及其总数。
        """
        filter_query, filter_params = self._build_filter_query(
            request_time_start,
            request_time_end,
            key_identifier,
            auth_key_alias,
            model_name,
            is_success,
        )

        async with aiosqlite.connect(self.db_path) as db:
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM request_logs {filter_query}"
            cursor = await db.execute(count_query, filter_params)
            result = await cursor.fetchone()
            total_count = result[0] if result else 0
            # 获取分页日志
            logs_query = f"SELECT * FROM request_logs {filter_query} ORDER BY request_time DESC LIMIT ? OFFSET ?"
            logs_params = filter_params + [limit, offset]
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(logs_query, logs_params)
            rows = await cursor.fetchall()
            logs = [
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
            return logs, total_count
