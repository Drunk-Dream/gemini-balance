from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

import pytz
from fastapi import Depends
from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.core.logging import app_logger
from backend.app.services.key_managers import background_tasks
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
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


def get_key_db_manager(
    settings: Settings = Depends(get_settings),
) -> DBManager:
    db_manager: DBManager
    if settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteDBManager(settings)
    else:
        raise ValueError(f"Unsupported key manager type: {settings.DATABASE_TYPE}")
    return db_manager


class KeyStateManager:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        db_manager: DBManager = Depends(get_key_db_manager),
        request_log_manager: RequestLogManager = Depends(RequestLogManager),
    ):
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS
        self._db_manager = db_manager
        self._request_log_manager = request_log_manager

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

    async def get_next_key(self) -> Optional[str]:
        key_identifier = await self._db_manager.get_next_available_key()
        if key_identifier:
            await self._db_manager.move_to_use(key_identifier)
            # 启动一个定时任务，在超时后自动释放密钥
            task = asyncio.create_task(
                background_tasks.timeout_release_key(
                    key_identifier,
                    self._db_manager,
                    self._key_in_use_timeout_seconds,
                    self._api_key_failure_threshold,
                )
            )
            background_tasks.timeout_tasks[key_identifier] = task
        return key_identifier

    async def mark_key_fail(
        self, key_identifier: str, error_type: str, request_info: RequestInfo
    ):

        async with background_tasks.key_manager_lock:
            # 取消对应的超时任务
            if key_identifier in background_tasks.timeout_tasks:
                background_tasks.timeout_tasks[key_identifier].cancel()
                del background_tasks.timeout_tasks[key_identifier]

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
                background_tasks.wakeup_event.set()
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

        async with background_tasks.key_manager_lock:
            # 取消对应的超时任务
            model = request_info.model_id
            if key_identifier in background_tasks.timeout_tasks:
                background_tasks.timeout_tasks[key_identifier].cancel()
                del background_tasks.timeout_tasks[key_identifier]

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
        async with background_tasks.key_manager_lock:
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
                        await self._db_manager.save_key_state(
                            key_identifier, state
                        )  # 保存更新后的状态
                else:  # 如果 last_usage_time 不存在，也重置 usage_today
                    state.usage_today = {}
                    await self._db_manager.save_key_state(
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
        async with background_tasks.key_manager_lock:
            await self._db_manager.add_key(key_identifier, api_key)
            app_logger.info(f"Added new API key: {key_identifier}")
            return key_identifier

    async def delete_key(self, key_identifier: str):
        async with background_tasks.key_manager_lock:
            await self._db_manager.delete_key(key_identifier)
            app_logger.info(f"Deleted API key: {key_identifier}")

    async def reset_key_state(self, key_identifier: str):
        async with background_tasks.key_manager_lock:
            await self._db_manager.reset_key_state(key_identifier)
            app_logger.info(f"Reset state for API key: {key_identifier}")

    async def reset_all_key_states(self):
        async with background_tasks.key_manager_lock:
            await self._db_manager.reset_all_key_states()
            app_logger.info("Reset state for all API keys.")
