from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RequestLog(BaseModel):
    """
    请求日志条目的 Pydantic 模型。
    """

    id: Optional[int] = None  # 数据库自动生成
    request_id: str
    request_time: datetime
    key_identifier: str
    auth_key_alias: Optional[str] = None
    model_name: Optional[str] = None
    is_success: bool


class RequestLogsResponse(BaseModel):
    """
    请求日志列表和总数的响应模型。
    """

    logs: List[RequestLog]
    total: int
