import abc
from datetime import datetime
from typing import List, Optional

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
        根据过滤条件获取请求日志条目。
        如果某个参数为 None，则表示该列不作为过滤条件。
        """
        raise NotImplementedError
