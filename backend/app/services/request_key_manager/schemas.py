import hashlib
import time

from pydantic import BaseModel, Field, computed_field


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


class KeyCounts(BaseModel):
    total: int
    in_use: int
    cooled_down: int
    available: int


class ApiKey(BaseModel):
    """
    表示一个API密钥，并根据完整的密钥自动生成标识符和简介。
    """

    full: str

    @computed_field
    @property
    def identifier(self) -> str:
        """一个对日志友好的唯一密钥标识符。"""
        return f"key_sha256_{hashlib.sha256(self.full.encode()).hexdigest()[:8]}"

    @computed_field
    @property
    def brief(self) -> str:
        """一个对日志友好的缩略版密钥。"""
        return f"{self.full[:4]}...{self.full[-4:]}"
