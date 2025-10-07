from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.api.schemas.request_logs import ChartData  # 新增导入
from backend.app.core.security import get_current_user
from backend.app.services.request_key_manager.key_state_manager import KeyStateManager
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


@router.get(
    "/request_logs/daily_usage_chart",
    response_model=ChartData,
    summary="获取每日模型使用统计图表数据",
)
async def get_daily_model_usage_chart_endpoint(
    timezone_str: str = Query(
        "America/New_York", description="目标时区字符串，例如 'Asia/Shanghai'"
    ),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
    key_state_manager: KeyStateManager = Depends(KeyStateManager),
) -> ChartData:
    """
    获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
    按 key_identifier 的总使用量降序排序，并格式化为图表数据。
    """
    request_logs = await request_logs_manager.get_daily_model_usage_chart_stats(
        timezone_str=timezone_str
    )
    mapping = await key_state_manager.get_key_identifier_to_brief_dict()
    request_logs.labels = [mapping.get(label, label) for label in request_logs.labels]
    return request_logs
