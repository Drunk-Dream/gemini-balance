import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import pytz
from pydantic import BaseModel

from backend.app.core.config import Settings
from backend.app.core.logging import app_logger
from backend.app.services.base_service import RequestInfo
from backend.app.services.key_managers.db_manager import DBManager, KeyState


class KeyStatusResponse(BaseModel):
    key_identifier: str
    status: str
    cool_down_seconds_remaining: float
    daily_usage: Dict[str, int]
    failure_count: int
    cool_down_entry_count: int
    current_cool_down_seconds: int
    is_in_use: bool  # 新增字段


class KeyStateManager:
    def __init__(self, settings: Settings, db_manager: DBManager):
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._lock = asyncio.Lock()  # 用于保护 Redis 操作的本地锁
        self._background_task: Optional[asyncio.Task] = None
        self._wakeup_event = asyncio.Event()
        self._db_manager = db_manager
        self._key_states_cache: Dict[str, KeyState] = {}

    def _get_key_identifier(self, key: str) -> str:
        """生成一个对日志友好且唯一的密钥标识符"""
        import hashlib

        return f"key_sha256_{hashlib.sha256(key.encode()).hexdigest()[:8]}"

    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        key_state = await self._db_manager.get_key_state(key_identifier)
        return key_state.api_key if key_state else None

    async def initialize(self):
        await self._load_key_states_to_cache()

    async def _load_key_states_to_cache(self):
        states = await self._db_manager.get_all_key_states()
        self._key_states_cache = {state.key_identifier: state for state in states}

    async def _get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        if key_identifier not in self._key_states_cache:
            state = await self._db_manager.get_key_state(key_identifier)
            if state:
                self._key_states_cache[key_identifier] = state
        return self._key_states_cache.get(key_identifier)

    async def _save_key_state(self, key_identifier: str, state: KeyState):
        self._key_states_cache[key_identifier] = state
        await self._db_manager.save_key_state(key_identifier, state)

    async def get_next_key(self) -> Optional[str]:
        return await self._db_manager.get_next_available_key()

    async def mark_key_fail(
        self, key_identifier: str, error_type: str, request_info: RequestInfo
    ):
        async with self._lock:
            request_id = request_info.request_id
            state = await self._get_key_state(key_identifier)
            if not state:
                return

            state.request_fail_count += 1
            state.last_usage_time = time.time()

            should_cool_down = False
            if error_type in [
                "auth_error",
                "rate_limit_error",
                "unexpected_error",
            ]:  # 新增 unexpected_error
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if state.request_fail_count >= self._api_key_failure_threshold:
                    should_cool_down = True

            if should_cool_down:
                state.cool_down_entry_count += 1
                backoff_factor = 2 ** (state.cool_down_entry_count - 1)
                new_cool_down = self._initial_cool_down_seconds * backoff_factor
                state.current_cool_down_seconds = min(
                    new_cool_down, self._max_cool_down_seconds
                )
                state.cool_down_until = time.time() + state.current_cool_down_seconds
                await self._db_manager.move_to_cooldown(
                    key_identifier, state.cool_down_until
                )
                self._wakeup_event.set()
                app_logger.warning(
                    f"[Request ID: {request_id}] Key '{key_identifier}' cooled down for "
                    f"{state.current_cool_down_seconds:.2f}s due to {error_type}."
                )
            else:  # 如果不需要冷却，则释放密钥
                await self._db_manager.release_key_from_use(key_identifier)
                app_logger.info(
                    f"[Request ID: {request_id}] Key '{key_identifier}' released from "
                    f"use after {error_type} without cooldown."
                )

            await self._save_key_state(key_identifier, state)

    async def mark_key_success(self, key_identifier: str, model: str):
        async with self._lock:
            state = await self._get_key_state(key_identifier)
            if not state:
                return
            state.cool_down_entry_count = 0
            state.current_cool_down_seconds = self._initial_cool_down_seconds
            state.request_fail_count = 0
            state.last_usage_time = time.time()
            # 使用美国东部时区计算日期
            eastern_tz = pytz.timezone("America/New_York")
            # 从时间戳获取日期，并格式化为字符串
            current_date = datetime.fromtimestamp(time.time(), tz=eastern_tz).strftime(
                "%Y-%m-%d"
            )
            if state.last_usage_date != current_date:
                state.usage_today = {}
            state.usage_today[model] = state.usage_today.get(model, 0) + 1

            await self._save_key_state(key_identifier, state)
            await self._db_manager.reactivate_key(key_identifier)

    async def get_key_states(self) -> List[KeyStatusResponse]:
        async with self._lock:
            await self._load_key_states_to_cache()
            states_response = []
            now = time.time()
            eastern_tz = pytz.timezone("America/New_York")
            current_date = datetime.fromtimestamp(now, tz=eastern_tz).strftime(
                "%Y-%m-%d"
            )
            for key_identifier, state in self._key_states_cache.items():
                # 检查是否跨天，如果跨天则重置 daily_usage
                if state.last_usage_time:
                    if state.last_usage_date != current_date:
                        state.usage_today = {}
                        await self._save_key_state(
                            key_identifier, state
                        )  # 保存更新后的状态
                else:  # 如果 last_usage_time 不存在，也重置 usage_today
                    state.usage_today = {}
                    await self._save_key_state(
                        key_identifier, state
                    )  # 保存更新后的状态

                cool_down_remaining = max(0, state.cool_down_until - now)

                if state.is_in_use:
                    status = "in_use"
                elif cool_down_remaining > 0:
                    status = "cooling_down"
                else:
                    status = "active"

                states_response.append(
                    KeyStatusResponse(
                        key_identifier=key_identifier,
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=state.usage_today,
                        failure_count=state.request_fail_count,
                        cool_down_entry_count=state.cool_down_entry_count,
                        current_cool_down_seconds=state.current_cool_down_seconds,
                        is_in_use=state.is_in_use,  # 新增字段
                    )
                )
            return states_response

    async def add_key(self, api_key: str) -> str:
        key_identifier = self._get_key_identifier(api_key)
        async with self._lock:
            await self._db_manager.add_key(key_identifier, api_key)
            await self._load_key_states_to_cache()  # Refresh cache
            app_logger.info(f"Added new API key: {key_identifier}")
            return key_identifier

    async def delete_key(self, key_identifier: str):
        async with self._lock:
            await self._db_manager.delete_key(key_identifier)
            self._key_states_cache.pop(key_identifier, None)  # Remove from cache
            app_logger.info(f"Deleted API key: {key_identifier}")

    async def reset_key_state(self, key_identifier: str):
        async with self._lock:
            await self._db_manager.reset_key_state(key_identifier)
            await self._load_key_states_to_cache()  # Refresh cache
            app_logger.info(f"Reset state for API key: {key_identifier}")

    async def reset_all_key_states(self):
        async with self._lock:
            await self._db_manager.reset_all_key_states()
            await self._load_key_states_to_cache()  # Refresh cache
            app_logger.info("Reset state for all API keys.")

    async def _release_cooled_down_keys(self):
        while True:
            try:
                releasable_keys = await self._db_manager.get_releasable_keys()
                for key_identifier in releasable_keys:
                    async with self._lock:
                        state = await self._get_key_state(key_identifier)
                        if state and state.cool_down_until <= time.time():
                            state.cool_down_until = 0.0
                            state.request_fail_count = 0
                            await self._save_key_state(key_identifier, state)
                            await self._db_manager.reactivate_key(key_identifier)
                            app_logger.info(f"API key '{key_identifier}' reactivated.")

                self._wakeup_event.clear()
                await asyncio.wait_for(self._wakeup_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break

    async def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None
