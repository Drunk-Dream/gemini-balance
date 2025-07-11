import asyncio
import time
from collections import deque
from typing import Dict, List, Optional

from app.core.config import settings


class KeyManager:
    def __init__(self, api_keys: List[str], cool_down_seconds: int):
        if not api_keys:
            raise ValueError("API key list cannot be empty.")
        self._available_keys = deque(api_keys)
        self._cool_down_keys: Dict[str, float] = {}
        self._cool_down_seconds = cool_down_seconds
        self._lock = asyncio.Lock()

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            # 检查并恢复冷却时间已到的 key
            now = time.time()
            for key, cool_down_time in list(self._cool_down_keys.items()):
                if now >= cool_down_time:
                    self._available_keys.append(key)
                    del self._cool_down_keys[key]

            if not self._available_keys:
                return None

            # 轮询获取 key
            key = self._available_keys.popleft()
            self._available_keys.append(key)  # 放回队列末尾，实现轮询
            return key

    async def deactivate_key(self, key: str):
        async with self._lock:
            # 从可用队列中移除 (如果存在)
            if key in self._available_keys:
                # 使用 remove() 方法，如果 key 不在 deque 中会抛出 ValueError
                # 因此需要先检查 key 是否存在
                try:
                    self._available_keys.remove(key)
                except ValueError:
                    pass  # key 可能已经被其他操作移除，或者不在可用列表中
            # 放入冷却字典
            self._cool_down_keys[key] = time.time() + self._cool_down_seconds


key_manager = KeyManager(
    settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else [],
    settings.API_KEY_COOL_DOWN_SECONDS
)
