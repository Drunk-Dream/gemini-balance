from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from venv import logger

import pytz
from pydantic import BaseModel

from backend.app.core.logging import app_logger
from backend.app.services.request_logs import get_request_log_manager
from backend.app.services.request_logs.schemas import RequestLog

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.chat_service.base_service import RequestInfo
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
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS
        self._default_check_cooled_down_seconds = (
            settings.DEFAULT_CHECK_COOLED_DOWN_SECONDS
        )
        self._lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None
        self._wakeup_event = asyncio.Event()
        self._db_manager = db_manager
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        self._request_log_manager = get_request_log_manager(settings)

    def _get_key_identifier(self, key: str) -> str:
        """生成一个对日志友好且唯一的密钥标识符"""
        import hashlib

        return f"key_sha256_{hashlib.sha256(key.encode()).hexdigest()[:8]}"

    async def get_key_from_identifier(self, key_identifier: str) -> Optional[str]:
        key_state = await self._db_manager.get_key_state(key_identifier)
        return key_state.api_key if key_state else None

    async def _get_key_state(self, key_identifier: str) -> Optional[KeyState]:
        return await self._db_manager.get_key_state(key_identifier)

    async def _get_all_key_states(self) -> List[KeyState]:
        return await self._db_manager.get_all_key_states()

    async def _save_key_state(self, key_identifier: str, state: KeyState):
        await self._db_manager.save_key_state(key_identifier, state)

    async def _timeout_release_key(self, key_identifier: str):
        """
        在指定超时后释放密钥，并增加失败计数。
        """
        try:
            await asyncio.sleep(self._key_in_use_timeout_seconds)
            async with self._lock:
                state = await self._get_key_state(key_identifier)
                if state and state.is_in_use:  # 再次检查密钥是否仍在使用中
                    state.request_fail_count += 1
                    await self._save_key_state(key_identifier, state)
                    await self._db_manager.release_key_from_use(key_identifier)
                    app_logger.warning(
                        f"Key {key_identifier} released from use due to timeout. "
                    )
        except asyncio.CancelledError:
            app_logger.debug(f"Timeout task for key {key_identifier} was cancelled.")
        finally:
            # 无论任务是否完成或取消，都从字典中移除
            if key_identifier in self._timeout_tasks:
                del self._timeout_tasks[key_identifier]

    async def initialize(self):
        async with self._lock:
            keys_in_use = await self._db_manager.get_keys_in_use()
            for key in keys_in_use:
                logger.warning(f"Releasing {key} from use due to initialization.")
                await self._db_manager.release_key_from_use(key)

    async def get_next_key(self) -> Optional[str]:
        key_identifier = await self._db_manager.get_next_available_key()
        if key_identifier:
            await self._db_manager.move_to_use(key_identifier)
            # 启动一个定时任务，在超时后自动释放密钥
            task = asyncio.create_task(self._timeout_release_key(key_identifier))
            self._timeout_tasks[key_identifier] = task
        return key_identifier

    async def mark_key_fail(
        self, key_identifier: str, error_type: str, request_info: RequestInfo
    ):

        async with self._lock:
            # 取消对应的超时任务
            if key_identifier in self._timeout_tasks:
                self._timeout_tasks[key_identifier].cancel()
                del self._timeout_tasks[key_identifier]

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
            ]:
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if state.request_fail_count >= self._api_key_failure_threshold:
                    should_cool_down = True
                    error_type = "max_failures_error"

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
                    f"[Request ID: {request_id}] Key {key_identifier} cooled down for "
                    f"{state.current_cool_down_seconds:.2f}s due to {error_type}."
                )
            else:  # 如果不需要冷却，则释放密钥
                await self._db_manager.release_key_from_use(key_identifier)
                app_logger.info(
                    f"[Request ID: {request_id}] Key {key_identifier} released from "
                    f"use after {error_type} without cooldown."
                )

            await self._save_key_state(key_identifier, state)

            # 记录请求日志
            log_entry = RequestLog(
                id=None,
                request_id=request_id,
                request_time=datetime.now(pytz.utc),
                key_identifier=key_identifier,
                auth_key_alias=request_info.auth_key_alias,
                model_name=request_info.model_id,
                is_success=False,
            )
            await self._request_log_manager.record_request_log(log_entry)

    async def mark_key_success(self, key_identifier: str, request_info: RequestInfo):

        async with self._lock:
            # 取消对应的超时任务
            model = request_info.model_id
            if key_identifier in self._timeout_tasks:
                self._timeout_tasks[key_identifier].cancel()
                del self._timeout_tasks[key_identifier]

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

            # 记录请求日志
            log_entry = RequestLog(
                id=None,
                request_id=request_info.request_id,
                request_time=datetime.now(pytz.utc),
                key_identifier=key_identifier,
                auth_key_alias=request_info.auth_key_alias,
                model_name=request_info.model_id,
                is_success=True,
            )
            await self._request_log_manager.record_request_log(log_entry)

    async def get_key_states(self) -> List[KeyStatusResponse]:
        async with self._lock:
            states_response = []
            now = time.time()
            eastern_tz = pytz.timezone("America/New_York")
            current_date = datetime.fromtimestamp(now, tz=eastern_tz).strftime(
                "%Y-%m-%d"
            )
            states = await self._get_all_key_states()

            for state in states:
                key_identifier = state.key_identifier
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
            app_logger.info(f"Added new API key: {key_identifier}")
            return key_identifier

    async def delete_key(self, key_identifier: str):
        async with self._lock:
            await self._db_manager.delete_key(key_identifier)
            app_logger.info(f"Deleted API key: {key_identifier}")

    async def reset_key_state(self, key_identifier: str):
        async with self._lock:
            await self._db_manager.reset_key_state(key_identifier)
            app_logger.info(f"Reset state for API key: {key_identifier}")

    async def reset_all_key_states(self):
        async with self._lock:
            await self._db_manager.reset_all_key_states()
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
                            app_logger.info(f"API key {key_identifier} reactivated.")

                # 获取下一个最近的冷却到期时间戳
                min_cool_down_until = await self._db_manager.get_min_cool_down_until()

                wait_time = self._default_check_cooled_down_seconds
                if min_cool_down_until:
                    now = time.time()
                    # 计算需要等待的秒数，确保不为负
                    calculated_wait = max(0, min_cool_down_until - now)
                    wait_time = calculated_wait

                self._wakeup_event.clear()
                # 使用计算出的时间或被事件唤醒
                await asyncio.wait_for(self._wakeup_event.wait(), timeout=wait_time)
            except asyncio.TimeoutError:
                # 超时是预期的行为，表示我们等待到了下一个检查点
                pass
            except asyncio.CancelledError:
                # 任务被取消，正常退出
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
