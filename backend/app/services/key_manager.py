import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from app.core.config import Settings
from pydantic import BaseModel, Field


class KeyState(BaseModel):
    key_identifier: str
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    usage_today: Dict[str, int] = Field(default_factory=dict)
    last_usage_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )
    last_usage_time: float = Field(default_factory=lambda: time.time())


class KeyStatusResponse(BaseModel):
    key_identifier: str
    status: str
    cool_down_seconds_remaining: float
    daily_usage: Dict[str, int]
    failure_count: int
    cool_down_entry_count: int
    current_cool_down_seconds: int


class KeyManager(ABC):
    """
    Abstract class for managing keys
    """

    def __init__(
        self,
        settings: Settings,
    ):
        if not settings.GOOGLE_API_KEYS:
            raise ValueError("No API keys provided")
        self._key_map = {
            self._get_key_identifier(key): key for key in settings.GOOGLE_API_KEYS
        }
        self._api_keys = list(self._key_map.keys())
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._lock = asyncio.Lock()  # 用于保护 Redis 操作的本地锁
        self._background_task: Optional[asyncio.Task] = None
        self._wakeup_event = asyncio.Event()

    def _get_key_identifier(self, key: str) -> str:
        """生成一个对日志友好且唯一的密钥标识符"""
        import hashlib

        return f"key_sha256_{hashlib.sha256(key.encode()).hexdigest()[:8]}"

    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        return self._key_map.get(key_identifier)

    @abstractmethod
    async def initialize(self):
        """初始化密钥管理器"""
        pass

    @abstractmethod
    async def get_next_key(self) -> Optional[str]:
        """获取下一个可用的 API 密钥"""
        pass

    @abstractmethod
    async def start_background_task(self):
        """启动后台任务"""
        pass

    @abstractmethod
    def stop_background_task(self):
        """停止后台任务"""
        pass

    @abstractmethod
    async def mark_key_fail(self, key_identifier: str, error_type: str):
        """标记密钥失败"""
        pass

    @abstractmethod
    async def mark_key_success(self, key_identifier: str):
        """标记密钥成功"""
        pass

    @abstractmethod
    async def record_usage(self, key_identifier: str, model: str):
        """记录密钥使用情况"""
        pass

    @abstractmethod
    async def get_key_states(self) -> List[KeyStatusResponse]:
        """获取所有密钥的状态"""
        pass
