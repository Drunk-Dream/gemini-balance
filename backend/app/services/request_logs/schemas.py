from datetime import datetime
from typing import List, Optional, Tuple

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
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error_type: Optional[str] = None
    key_brief: Optional[str] = None


class RequestLogsResponse(BaseModel):
    """
    请求日志列表和总数的响应模型。
    """

    logs: List[RequestLog]
    request_time_range: Optional[Tuple[datetime, datetime]] = None
    total: int
