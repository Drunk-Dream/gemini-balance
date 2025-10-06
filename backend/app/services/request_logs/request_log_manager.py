from datetime import datetime
from typing import Dict, Optional

from fastapi import Depends

from backend.app.api.api.schemas.request_logs import ChartData
from backend.app.core.config import Settings, get_settings
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.schemas import RequestLog, RequestLogsResponse
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
        limit: int = 100,
        offset: int = 0,
    ) -> RequestLogsResponse:
        """
        根据过滤条件获取请求日志条目及其总数。
        """
        logs, total = await self._db_manager.get_request_logs_with_count(
            request_time_start=request_time_start,
            request_time_end=request_time_end,
            limit=limit,
            offset=offset,
        )
        request_time_range = await self._db_manager.get_request_time_range()
        return RequestLogsResponse(
            logs=logs,
            total=total,
            request_time_range=request_time_range,
        )

    async def get_daily_model_usage_stats(
        self, timezone_str: str = "America/New_York"
    ) -> Dict[str, Dict[str, int]]:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数。
        """
        return await self._db_manager.get_daily_model_usage_stats(timezone_str)

    async def get_daily_model_usage_chart_stats(
        self, timezone_str: str = "America/New_York"
    ) -> ChartData:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
        按 key_identifier 的总使用量降序排序，并格式化为图表数据。
        """
        return await self._db_manager.get_daily_model_usage_chart_stats(timezone_str)

    async def get_auth_key_usage_stats(self) -> Dict[str, int]:
        """
        获取所有日志记录，并根据 auth_key_alias 进行分组，统计每个 auth_key_alias 的唯一请求数。
        """
        return await self._db_manager.get_auth_key_usage_stats()
