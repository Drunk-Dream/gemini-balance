from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.api.schemas.request_logs import (
    DailyUsageChartData,
    UsageStatsData,
    UsageStatsUnit,
)
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
    response_model=DailyUsageChartData,
    summary="获取每日模型使用统计图表数据",
)
async def get_daily_model_usage_chart_endpoint(
    timezone_str: str = Query(
        "America/New_York", description="目标时区字符串，例如 'Asia/Shanghai'"
    ),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
    key_state_manager: KeyStateManager = Depends(KeyStateManager),
) -> DailyUsageChartData:
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


@router.get(
    "/request_logs/usage_stats",
    response_model=UsageStatsData,
    summary="获取模型使用统计趋势图表数据",
)
async def get_usage_stats_endpoint(
    unit: UsageStatsUnit = Query(
        UsageStatsUnit.DAY, description="统计单位：'day', 'week', 'month'"
    ),
    offset: int = Query(
        0, description="时间偏移量，0表示当前周期，-1表示上一周期，以此类推"
    ),
    timezone_str: str = Query(
        "America/New_York", description="目标时区字符串，例如 'Asia/Shanghai'"
    ),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
    key_state_manager: KeyStateManager = Depends(KeyStateManager),
) -> UsageStatsData:
    """
    根据指定的时间单位（日、周、月）和偏移量，获取模型使用统计数据。
    """
    usage_stats = await request_logs_manager.get_usage_stats_by_period(
        unit=unit, offset=offset, timezone_str=timezone_str
    )
    # 这里不需要 key_identifier 到 key_brief 的映射，因为趋势图是按时间轴和 model_name 统计的
    return usage_stats
