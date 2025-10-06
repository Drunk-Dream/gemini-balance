from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import aiosqlite

from backend.app.api.api.schemas.request_logs import ChartData, ChartDataset
from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.schemas import RequestLog


class SQLiteRequestLogManager(RequestLogDBManager):
    """
    使用 aiosqlite 实现的请求日志数据库管理器。

    request_logs:
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        request_time REAL NOT NULL,
        key_identifier TEXT NOT NULL,
        auth_key_alias TEXT NOT NULL,
        model_name TEXT NOT NULL,
        is_success INTEGER NOT NULL
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        error_type TEXT,
        key_brief TEXT
        FOREIGN KEY (key_identifier) REFERENCES key_states(key_identifier) ON DELETE CASCADE,
        FOREIGN KEY (auth_key_alias) REFERENCES auth_keys(alias) ON DELETE CASCADE ON UPDATE CASCADE
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
                INSERT INTO request_logs (
                    request_id, request_time, key_identifier, auth_key_alias,
                    model_name, is_success, prompt_tokens, completion_tokens,
                    total_tokens, error_type, key_brief
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    log.request_id,
                    log.request_time.timestamp(),  # 存储为 Unix 时间戳
                    log.key_identifier,
                    log.auth_key_alias,
                    log.model_name,
                    int(log.is_success),  # 存储布尔值为整数 0 或 1
                    log.prompt_tokens,
                    log.completion_tokens,
                    log.total_tokens,
                    log.error_type,
                    log.key_brief,
                ),
            )
            await db.commit()
            app_logger.debug(f"Request log id: {log.request_id}")

    def _build_filter_query(
        self,
        request_time_start: Optional[datetime] = None,
        request_time_end: Optional[datetime] = None,
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

        return " ".join(query_parts), params

    async def get_request_logs_with_count(
        self,
        request_time_start: Optional[datetime] = None,
        request_time_end: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[RequestLog], int]:
        """
        根据过滤条件从 SQLite 数据库获取请求日志条目及其总数。
        """
        filter_query, filter_params = self._build_filter_query(
            request_time_start,
            request_time_end,
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
                    request_time=datetime.fromtimestamp(
                        row["request_time"], tz=ZoneInfo("UTC")
                    ),
                    key_identifier=row["key_identifier"],
                    auth_key_alias=row["auth_key_alias"],
                    model_name=row["model_name"],
                    is_success=bool(row["is_success"]),
                    prompt_tokens=row["prompt_tokens"],
                    completion_tokens=row["completion_tokens"],
                    total_tokens=row["total_tokens"],
                    error_type=row["error_type"],
                    key_brief=row["key_brief"],
                )
                for row in rows
            ]
            return logs, total_count

    async def get_daily_model_usage_stats(
        self, timezone_str: str
    ) -> Dict[str, Dict[str, int]]:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return {}

        # 获取当前日期在目标时区下的0点和24点
        now_in_tz = datetime.now(target_timezone)
        start_of_day_in_tz = now_in_tz.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_day_in_tz = (
            start_of_day_in_tz + timedelta(days=1) - timedelta(microseconds=1)
        )

        # 转换为 UTC 时间戳，因为数据库存储的是 UTC 时间戳
        start_timestamp_utc = start_of_day_in_tz.astimezone(ZoneInfo("UTC")).timestamp()
        end_timestamp_utc = end_of_day_in_tz.astimezone(ZoneInfo("UTC")).timestamp()

        app_logger.debug(
            f"Fetching daily stats for timezone {timezone_str}: "
            f"UTC start={start_timestamp_utc}, UTC end={end_timestamp_utc}"
        )

        query = """
            SELECT
                key_identifier,
                model_name,
                COUNT(*) as usage_count
            FROM
                request_logs
            WHERE
                is_success = 1 AND
                request_time >= ? AND
                request_time <= ?
            GROUP BY
                key_identifier,
                model_name
            ORDER BY
                key_identifier,
                model_name
        """
        params = [start_timestamp_utc, end_timestamp_utc]

        stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            for row in rows:
                key_identifier = row["key_identifier"]
                model_name = row["model_name"]
                usage_count = row["usage_count"]
                stats[key_identifier][model_name] = usage_count

        # 将 defaultdict 转换为普通的 dict
        return {k: dict(v) for k, v in stats.items()}

    async def get_daily_model_usage_chart_stats(self, timezone_str: str) -> ChartData:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
        按 key_identifier 的总使用量降序排序，并格式化为图表数据。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return ChartData(labels=[], datasets=[])

        now_in_tz = datetime.now(target_timezone)
        start_of_day_in_tz = now_in_tz.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_day_in_tz = (
            start_of_day_in_tz + timedelta(days=1) - timedelta(microseconds=1)
        )

        start_timestamp_utc = start_of_day_in_tz.astimezone(ZoneInfo("UTC")).timestamp()
        end_timestamp_utc = end_of_day_in_tz.astimezone(ZoneInfo("UTC")).timestamp()

        app_logger.debug(
            f"Fetching daily chart stats for timezone {timezone_str}: "
            f"UTC start={start_timestamp_utc}, UTC end={end_timestamp_utc}"
        )

        query = """
            WITH KeyUsage AS (
                SELECT
                    key_identifier,
                    model_name,
                    COUNT(*) as usage_count
                FROM request_logs
                WHERE is_success = 1 AND request_time >= ? AND request_time <= ?
                GROUP BY key_identifier, model_name
            ),
            KeyTotalUsage AS (
                SELECT
                    key_identifier,
                    SUM(usage_count) as total_usage
                FROM KeyUsage
                GROUP BY key_identifier
            )
            SELECT
                ku.key_identifier,
                ku.model_name,
                ku.usage_count
            FROM KeyUsage ku
            JOIN KeyTotalUsage ktu ON ku.key_identifier = ktu.key_identifier
            ORDER BY
                ktu.total_usage DESC,
                ku.key_identifier ASC
        """
        params = [start_timestamp_utc, end_timestamp_utc]

        labels: List[str] = []
        model_data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        all_model_names: set[str] = set()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            current_key_identifier: Optional[str] = None
            for row in rows:
                key_identifier = row["key_identifier"]
                model_name = row["model_name"]
                usage_count = row["usage_count"]

                if key_identifier != current_key_identifier:
                    labels.append(key_identifier)
                    current_key_identifier = key_identifier

                model_data[key_identifier][model_name] = usage_count
                all_model_names.add(model_name)

        datasets: List[ChartDataset] = []
        for model_name in sorted(list(all_model_names)):
            data_points: List[int] = []
            for key_label in labels:
                data_points.append(model_data[key_label].get(model_name, 0))
            datasets.append(ChartDataset(label=model_name, data=data_points))

        return ChartData(labels=labels, datasets=datasets)

    async def get_auth_key_usage_stats(self) -> Dict[str, int]:
        """
        获取所有日志记录，并根据 auth_key_alias 进行分组，统计每个 auth_key_alias 的唯一请求数。
        """
        query = """
            SELECT
                auth_key_alias,
                COUNT(DISTINCT request_id) as request_count
            FROM
                request_logs
            GROUP BY
                auth_key_alias
            ORDER BY
                auth_key_alias
        """
        stats: Dict[str, int] = {}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query)
            rows = await cursor.fetchall()

            for row in rows:
                auth_key_alias = row["auth_key_alias"]
                request_count = row["request_count"]
                stats[auth_key_alias] = request_count
        return stats

    async def get_request_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """
        获取数据库中记录的最小和最大请求时间。
        """
        query = """
            SELECT
                MIN(request_time) as min_time,
                MAX(request_time) as max_time
            FROM
                request_logs
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query)
            row = await cursor.fetchone()

            if row:
                min_time = datetime.fromtimestamp(row["min_time"], tz=ZoneInfo("UTC"))
                max_time = datetime.fromtimestamp(row["max_time"], tz=ZoneInfo("UTC"))
                return min_time, max_time

            return None
