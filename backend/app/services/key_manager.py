import asyncio
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logging import app_logger
from pydantic import BaseModel, Field


class KeyState(BaseModel):
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    usage_today: Dict[str, int] = Field(default_factory=dict)
    last_usage_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )


class KeyStatusResponse(BaseModel):
    key_identifier: str
    status: str
    cool_down_seconds_remaining: float
    daily_usage: Dict[str, int]
    failure_count: int
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
        self._key_states: Dict[str, KeyState] = {}
        self._initial_cool_down_seconds = cool_down_seconds
        self._api_key_failure_threshold = api_key_failure_threshold
        self._max_cool_down_seconds = max_cool_down_seconds
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._background_task: Optional[asyncio.Task] = None

        for key in api_keys:
            self._key_states[key] = KeyState(
                current_cool_down_seconds=self._initial_cool_down_seconds
            )

    async def _release_cooled_down_keys(self):
        while True:
            async with self._lock:
                now = time.time()
                keys_to_reactivate = []
                for key, state in self._key_states.items():
                    if (
                        state.cool_down_until > 0
                        and now >= state.cool_down_until
                        and key not in self._available_keys
                    ):
                        keys_to_reactivate.append(key)

                if keys_to_reactivate:
                    for key in keys_to_reactivate:
                        self._available_keys.append(key)
                        self._key_states[key].cool_down_until = 0.0
                        self._key_states[key].request_fail_count = 0
                    self._condition.notify_all()
            await asyncio.sleep(1)  # Check every second

    def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            while not self._available_keys:
                app_logger.info("No available keys, waiting...")
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    app_logger.warning("Timeout waiting for an available key.")
                    return None

            key = self._available_keys.popleft()
            self._available_keys.append(key)
            return key

    async def deactivate_key(self, key: str, error_type: str):
        async with self._lock:
            if key not in self._key_states:
                return

            key_state = self._key_states[key]
            key_state.request_fail_count += 1

            should_cool_down = False
            if error_type in ["auth_error", "rate_limit_error"]:
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if key_state.request_fail_count >= self._api_key_failure_threshold:
                    should_cool_down = True

            if should_cool_down:
                if key in self._available_keys:
                    try:
                        self._available_keys.remove(key)
                    except ValueError:
                        pass

                key_state.cool_down_entry_count += 1
                key_state.current_cool_down_seconds = min(
                    self._initial_cool_down_seconds
                    * (2 ** (key_state.cool_down_entry_count - 1)),
                    self._max_cool_down_seconds,
                )
                key_state.cool_down_until = (
                    time.time() + key_state.current_cool_down_seconds
                )
                app_logger.warning(
                    f"API key '...{key[-4:]}' entered cool-down for "
                    f"{key_state.current_cool_down_seconds:.2f} seconds "
                    f"due to {error_type}."
                )

    async def mark_key_success(self, key: str):
        async with self._lock:
            if key in self._key_states:
                # 成功时重置 cool_down_entry_count 和 current_cool_down_seconds
                key_state = self._key_states[key]
                key_state.cool_down_entry_count = 0
                key_state.current_cool_down_seconds = self._initial_cool_down_seconds

    async def record_usage(self, key: str, model: str):
        """记录指定 key 和模型的用量。"""
        async with self._lock:
            if key not in self._key_states:
                return

            key_state = self._key_states[key]
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 如果日期变更，重置当日用量
            if key_state.last_usage_date != today_str:
                key_state.usage_today = {}
                key_state.last_usage_date = today_str

            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            app_logger.debug(
                f"Key '...{key[-4:]}' usage for model '{model}': "
                f"{key_state.usage_today[model]}"
            )

    async def get_key_states(self) -> List[KeyStatusResponse]:
        """返回所有 API key 的详细状态列表。"""
        async with self._lock:
            states = []
            now = time.time()
            for key, key_state in self._key_states.items():
                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    KeyStatusResponse(
                        key_identifier=f"...{key[-4:]}",
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=key_state.usage_today,
                        failure_count=key_state.request_fail_count,
                        cool_down_entry_count=key_state.cool_down_entry_count,
                        current_cool_down_seconds=key_state.current_cool_down_seconds,
                    )
                )
            return states


key_manager = KeyManager(
    settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else [],
    settings.API_KEY_COOL_DOWN_SECONDS,
    settings.API_KEY_FAILURE_THRESHOLD,
    settings.MAX_COOL_DOWN_SECONDS,
)
