from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends

from backend.app.api.api.schemas.request_logs import (
    ChartDataset,
    DailyUsageChartData,
    UsageStatsData,
    UsageStatsUnit,
)
from backend.app.api.api.schemas.request_logs import (
    DailyModelSuccessRate,
    ModelSuccessRateStats,
    SuccessRateStatsResponse,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import app_logger
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.schemas import (
    RequestLog,
    RequestLogsResponse,
    TimePeriodDetails,
)
from backend.app.services.request_logs.sqlite_manager import SQLiteRequestLogManager


def get_request_log_db_manager(
    settings_obj: Settings = Depends(get_settings),
) -> RequestLogDBManager:
    """
    根据配置返回正确的 RequestLogDBManager 实例。
    """
    if settings_obj.DATABASE_TYPE == "sqlite":
        db_manager: RequestLogDBManager = SQLiteRequestLogManager(settings_obj)
    else:
        raise ValueError(f"Unsupported database type: {settings_obj.DATABASE_TYPE}")
    return db_manager


class RequestLogManager:
    """
    请求日志的主管理类，它将使用 RequestLogDBManager 的具体实现。
    """

    def __init__(
        self, db_manager: RequestLogDBManager = Depends(get_request_log_db_manager)
    ):
        self._db_manager = db_manager

    async def record_request_log(self, log: RequestLog) -> None:
        """
        记录一个请求日志条目。
        """
        await self._db_manager.record_request_log(log)

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
    ) -> RequestLogsResponse:
        """
        根据过滤条件获取请求日志条目及其总数。
        """
        logs, total = await self._db_manager.get_request_logs_with_count(
            request_time_start=request_time_start,
            request_time_end=request_time_end,
            key_identifier=key_identifier,
            auth_key_alias=auth_key_alias,
            model_name=model_name,
            is_success=is_success,
            limit=limit,
            offset=offset,
        )
        request_time_range = await self._db_manager.get_request_time_range()
        return RequestLogsResponse(
            logs=logs,
            total=total,
            request_time_range=request_time_range,
        )

    async def get_daily_model_success_rate_stats(
        self, days: int, timezone_str: str
    ) -> SuccessRateStatsResponse:
        """
        获取最近 `days` 天内每日各模型的成功率统计数据。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return SuccessRateStatsResponse(stats=[], models=[])

        now_in_tz = datetime.now(target_timezone)
        end_date = now_in_tz.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = (now_in_tz - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        sqlite_timezone_offset = self._get_timezone_offset_str(timezone_str)

        rows = await self._db_manager.get_daily_model_success_rate_stats(
            start_date, end_date, sqlite_timezone_offset
        )

        stats_by_date: Dict[str, Dict[str, DailyModelSuccessRate]] = defaultdict(dict)
        all_models = set()

        for row in rows:
            date_str = row["date"]
            model_name = row["model_name"]
            all_models.add(model_name)
            stats_by_date[date_str][model_name] = DailyModelSuccessRate(
                successful_requests=row["successful_requests"],
                total_requests=row["total_requests"],
            )

        result_stats: List[ModelSuccessRateStats] = []
        for day_offset in range(days):
            current_date = start_date.date() + timedelta(days=day_offset)
            date_str = current_date.isoformat()
            result_stats.append(
                ModelSuccessRateStats(
                    date=current_date, models=stats_by_date.get(date_str, {})
                )
            )

        return SuccessRateStatsResponse(
            stats=result_stats, models=sorted(list(all_models))
        )

    async def get_auth_key_usage_stats(self) -> Dict[str, int]:
        """
        获取所有日志记录，并根据 auth_key_alias 进行分组，统计每个 auth_key_alias 的唯一请求数。
        """
        return await self._db_manager.get_auth_key_usage_stats()

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

    def _calculate_time_period_details(
        self, unit: UsageStatsUnit, offset: int, num_periods: int, now_in_tz: datetime
    ) -> TimePeriodDetails:
        """
        根据指定的时间单位（日、周、月）和偏移量，计算时间段的详细信息。
        """
        start_date_display: datetime
        end_date_display: datetime
        period_labels: List[str] = []
        date_format: str
        group_by_format: str

        if unit == UsageStatsUnit.DAY:
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
            current_week_start = (now_in_tz + timedelta(weeks=offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(
                days=now_in_tz.weekday()
            )  # Monday is 0, Sunday is 6. Make Monday the start of the week.
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

        return TimePeriodDetails(
            start_of_range=start_date_display,
            end_of_range=end_date_display,
            period_labels=period_labels,
            date_format=date_format,
            group_by_format=group_by_format,
        )

    # --------------- Chart Data ---------------
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

        rows = await self._db_manager.query_daily_model_usage_stats(
            start_timestamp_utc, end_timestamp_utc
        )

        labels: List[str] = []
        model_data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        all_model_names: set[str] = set()
        key_identifier_to_key_brief: Dict[str, str] = {}

        current_key_identifier: Optional[str] = None
        for row in rows:
            key_identifier = row["key_identifier"]
            model_name = row["model_name"]
            usage_count = row["usage_count"]
            key_brief = row["key_brief"] if row["key_brief"] is not None else "null"

            if key_identifier != current_key_identifier:
                labels.append(key_identifier)
                key_identifier_to_key_brief[key_identifier] = key_brief
                current_key_identifier = key_identifier

            model_data[key_identifier][model_name] = usage_count
            all_model_names.add(model_name)

        datasets: List["ChartDataset"] = []
        for model_name in sorted(list(all_model_names)):
            data_points: List[int] = []
            for key_label in labels:
                data_points.append(model_data[key_label].get(model_name, 0))
            datasets.append(ChartDataset(label=model_name, data=data_points))

        label_briefs = [key_identifier_to_key_brief[label] for label in labels]

        return DailyUsageChartData(labels=label_briefs, datasets=datasets)

    async def get_usage_stats_by_period(
        self,
        unit: UsageStatsUnit,
        offset: int,
        num_periods: int,
        timezone_str: str,
        data_type: str,
    ) -> UsageStatsData:
        """
        根据指定的时间单位（日、周、月）和偏移量，获取模型使用或令牌统计数据。
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
        time_period_details = self._calculate_time_period_details(
            unit, offset, num_periods, now_in_tz
        )

        start_of_range = time_period_details.start_of_range
        end_of_range = time_period_details.end_of_range
        period_labels = time_period_details.period_labels
        date_format = time_period_details.date_format
        group_by_format = time_period_details.group_by_format

        start_timestamp_utc = start_of_range.astimezone(ZoneInfo("UTC")).timestamp()
        end_timestamp_utc = end_of_range.astimezone(ZoneInfo("UTC")).timestamp()

        app_logger.debug(
            f"Fetching {data_type} stats for unit={unit}, offset={offset}, timezone={timezone_str}: "
            f"UTC start={start_timestamp_utc}, UTC end={end_timestamp_utc}"
        )

        rows = await self._db_manager.query_usage_stats_by_period(
            start_timestamp_utc,
            end_timestamp_utc,
            group_by_format,
            sqlite_timezone_offset,
            data_type,
        )

        db_model_data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        all_model_names: set[str] = set()

        for row in rows:
            period_label = row["period_label"]
            model_name = row["model_name"]
            value = row["value"]

            if period_label and value is not None:
                db_model_data[period_label][model_name] = value
                all_model_names.add(model_name)

        datasets: List["ChartDataset"] = []
        for model_name in sorted(list(all_model_names)):
            data_points: List[int] = []
            for label in period_labels:
                data_points.append(db_model_data[label].get(model_name, 0))
            datasets.append(ChartDataset(label=model_name, data=data_points))

        return UsageStatsData(
            labels=period_labels,
            datasets=datasets,
            start_date=start_of_range.strftime(date_format),
            end_date=end_of_range.strftime(date_format),
        )

    async def get_daily_usage_heatmap_stats(
        self, data_type: str, timezone_str: str
    ) -> List[List[str | int]]:
        """
        获取指定时区内每日请求次数或 Token 用量的热力图数据。
        """
        try:
            target_timezone = ZoneInfo(timezone_str)
        except Exception:
            app_logger.error(f"Invalid timezone string: {timezone_str}")
            return []

        sqlite_timezone_offset = self._get_timezone_offset_str(timezone_str)
        if sqlite_timezone_offset == "+00:00" and timezone_str != "UTC":
            app_logger.warning(
                f"Could not determine specific offset for timezone '{timezone_str}', using UTC."
            )

        # 获取过去一年的数据
        now_in_tz = datetime.now(target_timezone)
        one_year_ago_in_tz = now_in_tz - timedelta(days=365)

        start_timestamp_utc = one_year_ago_in_tz.astimezone(ZoneInfo("UTC")).timestamp()
        end_timestamp_utc = now_in_tz.astimezone(ZoneInfo("UTC")).timestamp()

        app_logger.debug(
            f"Fetching daily usage heatmap stats for type={data_type}, timezone={timezone_str}: "
            f"UTC start={start_timestamp_utc}, UTC end={end_timestamp_utc}"
        )

        rows = await self._db_manager.query_daily_usage_heatmap_stats(
            start_timestamp_utc, end_timestamp_utc, sqlite_timezone_offset, data_type
        )

        heatmap_data: List[List[str | int]] = []
        for row in rows:
            date_str = row["date"]
            value = row["value"]
            heatmap_data.append([date_str, value])

        return heatmap_data
