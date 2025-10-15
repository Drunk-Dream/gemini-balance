import abc
from datetime import datetime
from typing import List, Optional, Tuple

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
    async def query_daily_usage_heatmap_stats(
        self,
        start_timestamp_utc: float,
        end_timestamp_utc: float,
        sqlite_timezone_offset: str,
        data_type: str,
    ) -> List[dict]:
        """
        查询指定 UTC 时间范围内每日的请求次数或 Token 用量，用于热力图。
        返回原始数据列表，每项包含 date, value。
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
    async def get_request_time_range(
        self,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        获取请求日志记录的时间范围。
        """
        raise NotImplementedError

    # --------------- Chart Data Query Methods ---------------
    @abc.abstractmethod
    async def query_daily_model_usage_stats(
        self, start_timestamp_utc: float, end_timestamp_utc: float
    ) -> List[dict]:
        """
        查询指定 UTC 时间范围内每天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数。
        返回原始数据列表，每项包含 key_identifier, key_brief, model_name, usage_count。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def query_usage_stats_by_period(
        self,
        start_timestamp_utc: float,
        end_timestamp_utc: float,
        group_by_format: str,
        sqlite_timezone_offset: str,
    ) -> List[dict]:
        """
        根据指定的时间单位和偏移量，查询模型使用统计数据。
        返回原始数据列表，每项包含 period_label, model_name, request_count。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def query_token_usage_stats_by_period(
        self,
        start_timestamp_utc: float,
        end_timestamp_utc: float,
        group_by_format: str,
        sqlite_timezone_offset: str,
    ) -> List[dict]:
        """
        根据指定的时间单位和偏移量，查询 token 使用统计数据。
        返回原始数据列表，每项包含 period_label, model_name, token_count。
        """
        raise NotImplementedError
