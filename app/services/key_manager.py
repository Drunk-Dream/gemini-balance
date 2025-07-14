import asyncio
import time
from collections import deque
from typing import Dict, List, Optional, TypedDict

from app.core.config import settings
from app.core.logging import app_logger


class KeyState(TypedDict):
    cool_down_until: float
    request_fail_count: int
    cool_down_entry_count: int
    current_cool_down_seconds: int


class KeyManager:
    def __init__(
        self,
        api_keys: List[str],
        cool_down_seconds: int,
        api_key_failure_threshold: int,
        max_cool_down_seconds: int,
    ):
        if not api_keys:
            raise ValueError("API key list cannot be empty.")
        self._available_keys = deque(api_keys)
        self._cool_down_keys: Dict[str, float] = {}  # 仍然保留，用于快速检查是否在冷却
        self._key_states: Dict[str, KeyState] = {}
        self._initial_cool_down_seconds = cool_down_seconds
        self._api_key_failure_threshold = api_key_failure_threshold
        self._max_cool_down_seconds = max_cool_down_seconds
        self._lock = asyncio.Lock()

        for key in api_keys:
            self._key_states[key] = {
                "cool_down_until": 0.0,
                "request_fail_count": 0,
                "cool_down_entry_count": 0,
                "current_cool_down_seconds": self._initial_cool_down_seconds,
            }

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            now = time.time()
            keys_to_reactivate = []

            # 检查并恢复冷却时间已到的 key
            for key, cool_down_time in list(self._cool_down_keys.items()):
                if now >= cool_down_time:
                    keys_to_reactivate.append(key)

            for key in keys_to_reactivate:
                if key not in self._available_keys:  # 避免重复添加
                    self._available_keys.append(key)
                del self._cool_down_keys[key]
                # 冷却恢复时，重置 request_fail_count
                if key in self._key_states:
                    self._key_states[key]["request_fail_count"] = 0

            if not self._available_keys:
                return None

            # 轮询获取 key
            key = self._available_keys.popleft()
            self._available_keys.append(key)  # 放回队列末尾，实现轮询
            return key

    async def deactivate_key(self, key: str, error_type: str):
        async with self._lock:
            if key not in self._key_states:
                # 如果 key 不在管理中，直接返回
                return

            key_state = self._key_states[key]
            key_state["request_fail_count"] += 1

            should_cool_down = False
            if error_type in ["auth_error", "rate_limit_error"]:
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if key_state["request_fail_count"] >= self._api_key_failure_threshold:
                    should_cool_down = True

            if should_cool_down:
                # 从可用队列中移除 (如果存在)
                if key in self._available_keys:
                    try:
                        self._available_keys.remove(key)
                    except ValueError:
                        pass

                key_state["cool_down_entry_count"] += 1
                # 动态增加冷却时长，例如指数退避
                key_state["current_cool_down_seconds"] = (
                    self._initial_cool_down_seconds
                    * (2 ** (key_state["cool_down_entry_count"] - 1))
                )
                # 限制最大冷却时间，避免过长
                max_cool_down = self._max_cool_down_seconds
                if key_state["current_cool_down_seconds"] > max_cool_down:
                    key_state["current_cool_down_seconds"] = max_cool_down

                key_state["cool_down_until"] = (
                    time.time() + key_state["current_cool_down_seconds"]
                )
                self._cool_down_keys[key] = key_state["cool_down_until"]
                app_logger.warning(
                    f"API key '{key[-4:]}...' entered cool-down for "
                    f"{key_state['current_cool_down_seconds']:.2f} seconds "
                    f"due to {error_type}."
                )

    async def mark_key_success(self, key: str):
        async with self._lock:
            if key in self._key_states:
                # 成功时重置 cool_down_entry_count 和 current_cool_down_seconds
                self._key_states[key]["cool_down_entry_count"] = 0
                self._key_states[key][
                    "current_cool_down_seconds"
                ] = self._initial_cool_down_seconds


key_manager = KeyManager(
    settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else [],
    settings.API_KEY_COOL_DOWN_SECONDS,
    settings.API_KEY_FAILURE_THRESHOLD,
    settings.MAX_COOL_DOWN_SECONDS,
)
