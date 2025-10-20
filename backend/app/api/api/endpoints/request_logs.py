from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.api.schemas.request_logs import (
    DailyUsageChartData,
    DailyUsageHeatmapData,
    HourlySuccessRateChartData,  # 导入 DailyUsageHeatmapData
    UsageStatsData,
    UsageStatsUnit,
)
from backend.app.api.api.schemas.request_logs import SuccessRateStatsResponse
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
    # key_state_manager: KeyStateManager = Depends(KeyStateManager),
) -> DailyUsageChartData:
    """
    获取指定时区内当天成功的请求，并统计每个 key_identifier 下，每个 model_name 的使用次数，
    按 key_identifier 的总使用量降序排序，并格式化为图表数据。
    """
    request_logs = await request_logs_manager.get_daily_model_usage_chart_stats(
        timezone_str=timezone_str
    )
    return request_logs


@router.get(
    "/request_logs/usage_stats",
    response_model=UsageStatsData,
    summary="获取使用统计趋势图表数据",
)
async def get_usage_stats_endpoint(
    type: str = Query(..., description="数据类型：'requests' 或 'tokens'"),
    unit: UsageStatsUnit = Query(
        UsageStatsUnit.DAY, description="统计单位：'day', 'week', 'month'"
    ),
    offset: int = Query(
        0, description="时间偏移量，0表示当前周期，-1表示上一周期，以此类推"
    ),
    num_periods: int = Query(7, description="要显示的周期数量"),
    timezone_str: str = Query(
        "America/New_York", description="目标时区字符串，例如 'Asia/Shanghai'"
    ),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
) -> UsageStatsData:
    """
    根据指定的时间单位（日、周、月）和偏移量，获取模型使用或令牌统计数据。
    """
    return await request_logs_manager.get_usage_stats_by_period(
        unit=unit,
        offset=offset,
        num_periods=num_periods,
        timezone_str=timezone_str,
        data_type=type,
    )


@router.get(
    "/request_logs/daily_usage_heatmap",
    response_model=DailyUsageHeatmapData,
    summary="获取每日使用热力图数据",
)
async def get_daily_usage_heatmap_endpoint(
    type: str = Query(..., description="数据类型：'requests' 或 'tokens'"),
    timezone_str: str = Query(
        "America/New_York", description="目标时区字符串，例如 'Asia/Shanghai'"
    ),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
) -> DailyUsageHeatmapData:
    """
    获取指定时区内每日请求次数或 Token 用量的热力图数据。
    """
    return await request_logs_manager.get_daily_usage_heatmap_stats(
        data_type=type, timezone_str=timezone_str
    )


@router.get(
    "/stats/success-rate",
    response_model=SuccessRateStatsResponse,
    summary="获取每日模型请求成功率统计",
)
async def get_daily_model_success_rate_stats(
    days: int = Query(7, ge=1, le=90, description="统计最近N天的数据"),
    timezone_str: str = Query("UTC", description="IANA 时区名称"),
    current_user: str = Depends(get_current_user),
    request_logs_manager: RequestLogManager = Depends(RequestLogManager),
):
    """
    根据指定的天数范围，获取每日各模型的请求成功与总次数。
    """
    return await request_logs_manager.get_daily_model_success_rate_stats(
        days=days, timezone_str=timezone_str
    )


@router.get(
    "/stats/hourly-success-rate",
    response_model=HourlySuccessRateChartData,
    summary="获取每小时模型成功率统计",
)
async def get_hourly_model_success_rate(
    days: int = Query(30, ge=1, le=365, description="查询最近的天数"),
    timezone: str = Query("UTC", description="客户端IANA时区字符串"),
    log_manager: RequestLogManager = Depends(RequestLogManager),
):
    """
    获取最近 `days` 天内，按一天24小时划分的各模型平均请求成功率。
    - **days**: 查询的范围，例如 30 表示最近30天。
    - **timezone**: 用于确定日期范围的IANA时区，例如 `Asia/Shanghai`。
    """
    return await log_manager.get_hourly_model_success_rate_stats(
        days=days, timezone_str=timezone
    )
