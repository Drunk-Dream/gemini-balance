from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import aiosqlite

from backend.app.api.api.schemas.request_logs import (
    ChartDataset,
    DailyUsageChartData,
    UsageStatsData,
    UsageStatsUnit,
)
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

    def _get_timezone_offset_str(self, timezone_str: str) -> str:
        """
        将 IANA 时区字符串转换为 SQLite strftime 函数支持的 UTC 偏移量字符串。
        例如 'Asia/Shanghai' -> '+8 hours' 或 '+08:00'。
        """
        try:
            tz = ZoneInfo(timezone_str)
            # 获取当前时间的 UTC 偏移量
            # 注意：这里假设时区偏移在一天内是恒定的，对于 DST 可能会有不准确，
            # 但对于 SQLite 的 strftime 来说，它需要一个固定的偏移量。
            # 实际应用中，如果需要精确处理 DST，可能需要更复杂的逻辑或在应用层进行时间转换。
            now = datetime.now(tz)
            offset = now.utcoffset()
            if offset is None:
                app_logger.error(
                    f"Could not get UTC offset for timezone '{timezone_str}'"
                )
                return "+00:00"  # 默认返回 UTC

            offset_seconds = int(offset.total_seconds())

            # 将秒转换为小时和分钟
            hours = offset_seconds // 3600
            minutes = abs((offset_seconds % 3600) // 60)  # 使用 abs 确保分钟是正数

            # 格式化为 '+HH:MM' 或 '-HH:MM'
            return f"{hours:+03d}:{minutes:02d}"
        except Exception as e:
            app_logger.error(
                f"Error converting timezone '{timezone_str}' to offset: {e}"
            )
            return "+00:00"  # 默认返回 UTC

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

    async def get_daily_model_usage_chart_stats(
        self, timezone_str: str
    ) -> DailyUsageChartData:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
        按 key_identifier 的总使用量降序排序，并格式化为图表数据。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return DailyUsageChartData(labels=[], datasets=[])

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

        return DailyUsageChartData(labels=labels, datasets=datasets)

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

    async def get_usage_stats_by_period(
        self, unit: UsageStatsUnit, offset: int, timezone_str: str
    ) -> UsageStatsData:
        """
        根据指定的时间单位（日、周、月）和偏移量，获取模型使用统计数据。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return UsageStatsData(labels=[], datasets=[], start_date="", end_date="")

        sqlite_timezone_offset = self._get_timezone_offset_str(timezone_str)
        if sqlite_timezone_offset == "+00:00" and timezone_str != "UTC":
            app_logger.warning(
                f"Could not determine specific offset for timezone '{timezone_str}', using UTC."
            )

        now_in_tz = datetime.now(target_timezone)
        start_date_display: datetime
        end_date_display: datetime
        period_labels: List[str] = []

        if unit == UsageStatsUnit.DAY:
            num_periods = 7
            current_period_start = (now_in_tz + timedelta(days=offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start_of_range = current_period_start - timedelta(days=num_periods - 1)
            end_of_range = current_period_start.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            date_format = "%Y-%m-%d"
            group_by_format = "%Y-%m-%d"

            for i in range(num_periods):
                date = start_of_range + timedelta(days=i)
                period_labels.append(date.strftime(date_format))

            start_date_display = start_of_range
            end_date_display = end_of_range

        elif unit == UsageStatsUnit.WEEK:
            num_periods = 7
            current_week_start = (now_in_tz + timedelta(weeks=offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(
                days=(now_in_tz.weekday() + 1) % 7
            )  # Monday is 0, Sunday is 6. Make Sunday the start of the week.
            start_of_range = current_week_start - timedelta(weeks=num_periods - 1)
            end_of_range = (current_week_start + timedelta(days=6)).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            date_format = "%Y-%m-%d"
            group_by_format = (
                "%Y-%W"  # %W for week number (Sunday as first day of week)
            )

            for i in range(num_periods):
                week_start = start_of_range + timedelta(weeks=i)
                period_labels.append(week_start.strftime(group_by_format))

            start_date_display = start_of_range
            end_date_display = end_of_range

        elif unit == UsageStatsUnit.MONTH:
            num_periods = 6
            current_month_start = (now_in_tz + timedelta(days=30 * offset)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            # Adjust to the correct month if timedelta(days=30*offset) overshoots
            while current_month_start.month != (now_in_tz.month + offset - 1) % 12 + 1:
                current_month_start = (current_month_start - timedelta(days=1)).replace(
                    day=1
                )

            start_of_range = current_month_start
            for _ in range(num_periods - 1):
                start_of_range = (start_of_range - timedelta(days=1)).replace(day=1)

            end_of_range = (
                current_month_start.replace(day=28) + timedelta(days=4)
            ).replace(hour=23, minute=59, second=59, microsecond=999999)
            end_of_range = end_of_range - timedelta(days=end_of_range.day)
            date_format = "%Y-%m"
            group_by_format = "%Y-%m"

            current_label_date = start_of_range
            for _ in range(num_periods):
                period_labels.append(current_label_date.strftime(date_format))
                # Move to the first day of the next month
                if current_label_date.month == 12:
                    current_label_date = current_label_date.replace(
                        year=current_label_date.year + 1, month=1, day=1
                    )
                else:
                    current_label_date = current_label_date.replace(
                        month=current_label_date.month + 1, day=1
                    )

            start_date_display = start_of_range
            end_date_display = end_of_range

        else:
            raise ValueError(f"Unsupported unit: {unit}")

        start_timestamp_utc = start_of_range.astimezone(ZoneInfo("UTC")).timestamp()
        end_timestamp_utc = end_of_range.astimezone(ZoneInfo("UTC")).timestamp()

        app_logger.debug(
            f"Fetching usage stats for unit={unit}, offset={offset}, timezone={timezone_str}: "
            f"UTC start={start_timestamp_utc}, UTC end={end_timestamp_utc}"
        )

        query = f"""
            SELECT
                strftime('{group_by_format}', request_time, 'unixepoch', '{sqlite_timezone_offset}') as period_label,
                model_name,
                COUNT(DISTINCT request_id) as request_count
            FROM request_logs
            WHERE is_success = 1 AND request_time >= ? AND request_time <= ?
            GROUP BY period_label, model_name
            ORDER BY period_label ASC, model_name ASC
        """
        params = [start_timestamp_utc, end_timestamp_utc]

        db_model_data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        all_model_names: set[str] = set()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            for row in rows:
                period_label = row["period_label"]
                model_name = row["model_name"]
                request_count = row["request_count"]

                if period_label:  # 确保 period_label 不是 None
                    db_model_data[period_label][model_name] = request_count
                    all_model_names.add(model_name)

        datasets: List[ChartDataset] = []
        for model_name in sorted(list(all_model_names)):
            data_points: List[int] = []
            for label in period_labels:
                data_points.append(db_model_data[label].get(model_name, 0))
            datasets.append(ChartDataset(label=model_name, data=data_points))

        return UsageStatsData(
            labels=period_labels,
            datasets=datasets,
            start_date=start_date_display.strftime(date_format),
            end_date=end_date_display.strftime(date_format),
        )
