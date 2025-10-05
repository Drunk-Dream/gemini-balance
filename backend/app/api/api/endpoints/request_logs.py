from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.core.security import get_current_user
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.schemas import RequestLogsResponse

router = APIRouter()


@router.get(
    "/request_logs",
    response_model=RequestLogsResponse,
    summary="获取请求日志",
)
async def get_request_logs_endpoint(
    request_time_start: Optional[datetime] = Query(
        None, description="请求开始时间 (ISO 8601 格式)"
    ),
    request_time_end: Optional[datetime] = Query(
        None, description="请求结束时间 (ISO 8601 格式)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="返回的日志条目数量限制"),
    offset: int = Query(0, ge=0, description="跳过的日志条目数量"),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
) -> RequestLogsResponse:
    """
    根据过滤条件获取请求日志条目及其总数。
    """
    return await request_logs_manager.get_request_logs(
        request_time_start=request_time_start,
        request_time_end=request_time_end,
        limit=limit,
        offset=offset,
    )
