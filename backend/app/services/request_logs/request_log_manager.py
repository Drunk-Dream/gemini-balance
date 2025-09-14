from datetime import datetime
from typing import List, Optional

from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.schemas import RequestLog


class RequestLogManager:
    """
    请求日志的主管理类，它将使用 RequestLogDBManager 的具体实现。
    """

    def __init__(self, db_manager: RequestLogDBManager):
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
    ) -> List[RequestLog]:
        """
        根据过滤条件获取请求日志条目。
        """
        return await self._db_manager.get_request_logs(
            request_time_start=request_time_start,
            request_time_end=request_time_end,
            key_identifier=key_identifier,
            auth_key_alias=auth_key_alias,
            model_name=model_name,
            is_success=is_success,
            limit=limit,
            offset=offset,
        )
