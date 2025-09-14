from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from backend.app.core.security import get_current_user
from backend.app.services.request_logs import get_request_log_manager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.schemas import RequestLog

router = APIRouter()


@router.get(
    "/request-logs",
    response_model=List[RequestLog],
    summary="获取请求日志",
)
async def get_request_logs_endpoint(
    request_time_start: Optional[datetime] = Query(
        None, description="请求开始时间 (ISO 8601 格式)"
    ),
    request_time_end: Optional[datetime] = Query(
        None, description="请求结束时间 (ISO 8601 格式)"
    ),
    key_identifier: Optional[str] = Query(None, description="API 密钥标识符"),
    auth_key_alias: Optional[str] = Query(None, description="认证密钥别名"),
    model_name: Optional[str] = Query(None, description="模型名称"),
    is_success: Optional[bool] = Query(None, description="请求是否成功"),
    limit: int = Query(100, ge=1, le=1000, description="返回的日志条目数量限制"),
    offset: int = Query(0, ge=0, description="跳过的日志条目数量"),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(get_request_log_manager),
) -> List[RequestLog]:
    """
    根据过滤条件获取请求日志条目。
    """
    return await request_logs_manager.get_request_logs(
        request_time_start=request_time_start,
        request_time_end=request_time_end,
        key_identifier=key_identifier,
        auth_key_alias=auth_key_alias,
        model_name=model_name,
        is_success=is_success,
        limit=limit,
        offset=offset,
    )
