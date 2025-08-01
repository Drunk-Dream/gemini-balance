import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.core.config import Settings
from app.core.logging import app_logger
from app.services.key_manager import KeyManager, KeyState, KeyStatusResponse
from app.services.key_managers.db_manager import DBManager


class KeyStateManager(KeyManager):
    def __init__(self, settings: Settings, db_manager: DBManager):
        super().__init__(settings)
        self._db_manager = db_manager
        self._key_states_cache: Dict[str, KeyState] = {}

    async def initialize(self):
        await self._db_manager.initialize()
        await self._db_manager.sync_keys(set(self._api_keys))
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

    async def mark_key_fail(self, key_identifier: str, error_type: str):
        async with self._lock:
            state = await self._get_key_state(key_identifier)
            if not state:
                return

            state.request_fail_count += 1
            state.last_usage_time = time.time()

            should_cool_down = False
            if error_type in ["auth_error", "rate_limit_error"]:
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
                    f"Key '{key_identifier}' cooled down for "
                    f"{state.current_cool_down_seconds:.2f}s due to {error_type}."
                )
            await self._save_key_state(key_identifier, state)

    async def mark_key_success(self, key_identifier: str):
        async with self._lock:
            state = await self._get_key_state(key_identifier)
            if state:
                state.cool_down_entry_count = 0
                state.current_cool_down_seconds = self._initial_cool_down_seconds
                state.request_fail_count = 0
                state.last_usage_time = time.time()
                await self._save_key_state(key_identifier, state)
                await self._db_manager.reactivate_key(key_identifier)

    async def record_usage(self, key_identifier: str, model: str):
        async with self._lock:
            state = await self._get_key_state(key_identifier)
            if not state:
                return

            today_str = datetime.now().strftime("%Y-%m-%d")
            if state.last_usage_date != today_str:
                state.usage_today = {}
                state.last_usage_date = today_str

            state.usage_today[model] = state.usage_today.get(model, 0) + 1
            await self._save_key_state(key_identifier, state)

    async def get_key_states(self) -> List[KeyStatusResponse]:
        async with self._lock:
            await self._load_key_states_to_cache()
            states_response = []
            now = time.time()
            for key_identifier, state in self._key_states_cache.items():
                cool_down_remaining = max(0, state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"
                states_response.append(
                    KeyStatusResponse(
                        key_identifier=key_identifier,
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=state.usage_today,
                        failure_count=state.request_fail_count,
                        cool_down_entry_count=state.cool_down_entry_count,
                        current_cool_down_seconds=state.current_cool_down_seconds,
                    )
                )
            return states_response

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
