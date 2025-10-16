import time

from pydantic import BaseModel, Field


class KeyState(BaseModel):
    key_identifier: str
    api_key: str  # 新增字段
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    last_usage_time: float = Field(default_factory=lambda: time.time())
    is_in_use: bool = False  # 新增字段，指示key是否在使用中
    is_cooled_down: bool = False  # 新增字段，指示key是否在冷却中


class KeyType(BaseModel):
    identifier: str
    brief: str
    full: str


class KeyCounts(BaseModel):
    total: int
    in_use: int
    cooled_down: int
    available: int
