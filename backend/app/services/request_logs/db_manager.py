import abc
from datetime import datetime
from typing import List, Optional, Tuple

from backend.app.api.api.schemas.request_logs import ChartData
from backend.app.services.request_logs.schemas import RequestLog


class RequestLogDBManager(abc.ABC):
    """
    请求日志数据库管理器的抽象基类。
    定义了记录和获取请求日志的方法。
    """

    @abc.abstractmethod
    async def record_request_log(self, log: RequestLog) -> None:
        """
        记录一个请求日志条目。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_auth_key_usage_stats(self) -> dict[str, int]:
        """
        获取所有日志记录，并根据 auth_key_alias 进行分组，统计每个 auth_key_alias 的唯一请求数。
        """
        raise NotImplementedError

    @abc.abstractmethod
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
        根据过滤条件获取请求日志条目及其总数。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_daily_model_usage_stats(
        self, timezone_str: str
    ) -> dict[str, dict[str, int]]:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_daily_model_usage_chart_stats(self, timezone_str: str) -> ChartData:
        """
        获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
        按 key_identifier 的总使用量降序排序，并格式化为图表数据。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_request_time_range(
        self,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        获取请求日志记录的时间范围。
        """
        raise NotImplementedError
