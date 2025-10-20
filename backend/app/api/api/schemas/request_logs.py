from datetime import date
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


class ChartDataset(BaseModel):
    label: str
    data: List[float] | List[int]
    # 可以根据 Chart.js 的需求添加更多字段，例如 backgroundColor, borderColor 等
    # backgroundColor: Optional[List[str]] = None
    # borderColor: Optional[List[str]] = None
    # borderWidth: Optional[int] = None


class ChartData(BaseModel):
    labels: List[str]
    datasets: List["ChartDataset"]


class UsageStatsUnit(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


DailyUsageHeatmapData = List[List[str | int]]


class ModelSuccessRateStats(BaseModel):
    date: date
    models: Dict[str, float]


class SuccessRateStatsResponse(BaseModel):
    stats: List[ModelSuccessRateStats]
    models: List[str]
