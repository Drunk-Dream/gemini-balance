from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends
from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.core.logging import app_logger
from backend.app.services.key_managers.background_tasks import (
    get_background_task_manager,
    with_key_manager_lock,
)
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.schemas import RequestLog

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.key_managers.background_tasks import BackgroundTaskManager
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
        background_task_manager: BackgroundTaskManager = Depends(
            get_background_task_manager
        ),
    ):
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS
        self._db_manager = db_manager
        self._request_log_manager = request_log_manager
        self._background_task_manager = background_task_manager

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

    async def get_next_key(self, request_id: str, auth_key_alias: str) -> Optional[str]:
        key_identifier = await self._db_manager.get_next_available_key()
        if key_identifier:
            await self._db_manager.move_to_use(key_identifier)
            # 启动一个定时任务，在超时后自动释放密钥
            self._background_task_manager.create_timeout_task(
                key_identifier,
                self._key_in_use_timeout_seconds,
                request_id,
                auth_key_alias,
                self,
            )
        return key_identifier

    @with_key_manager_lock
    async def mark_key_fail(
        self,
        key_identifier: str,
        error_type: str,
        request_id: str,
        auth_key_alias: Optional[str],
    ):
        # 取消对应的超时任务
        self._background_task_manager.cancel_timeout_task(key_identifier)

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
        elif error_type in [
            "other_http_error",
            "request_error",
            "use_timeout_error",
            "streaming_completion_error",
        ]:
            if state.request_fail_count >= self._api_key_failure_threshold:
                should_cool_down = True
                error_type += " & max_failures_error"

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
            self._background_task_manager.wakeup_event.set()
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
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key_identifier,
            auth_key_alias=auth_key_alias,
            model_name="unknown",  # model_id is not passed, use "unknown" or retrieve from state if possible
            is_success=False,
        )
        await self._request_log_manager.record_request_log(log_entry)

    @with_key_manager_lock
    async def mark_key_success(
        self,
        key_identifier: str,
        request_id: str,
        auth_key_alias: Optional[str],
        model_id: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ):
        # 取消对应的超时任务
        self._background_task_manager.cancel_timeout_task(key_identifier)

        state = await self._get_key_state(key_identifier)
        if not state:
            return
        state.cool_down_entry_count = 0
        state.current_cool_down_seconds = self._initial_cool_down_seconds
        state.request_fail_count = 0
        state.last_usage_time = time.time()

        await self._save_key_state(key_identifier, state)
        await self._db_manager.reactivate_key(key_identifier)

        # 记录请求日志
        log_entry = RequestLog(
            id=None,
            request_id=request_id,
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key_identifier,
            auth_key_alias=auth_key_alias,
            model_name=model_id,
            is_success=True,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        await self._request_log_manager.record_request_log(log_entry)

    @with_key_manager_lock
    async def get_key_states(self) -> List[KeyStatusResponse]:
        states_response = []
        now = time.time()
        # 获取当天的模型使用统计
        daily_usage_stats = (
            await self._request_log_manager.get_daily_model_usage_stats()
        )
        states = await self._get_all_key_states()

        for state in states:
            key_identifier = state.key_identifier
            cool_down_remaining = max(0, state.cool_down_until - now)

            if state.is_in_use:
                status = "in_use"
            elif cool_down_remaining > 0:
                status = "cooling_down"
            else:
                status = "active"

            # 从统计数据中获取当前 key_identifier 的 daily_usage，如果不存在则为空字典
            key_daily_usage = daily_usage_stats.get(key_identifier, {})

            states_response.append(
                KeyStatusResponse(
                    key_identifier=key_identifier,
                    status=status,
                    cool_down_seconds_remaining=round(cool_down_remaining, 2),
                    daily_usage=key_daily_usage,
                    failure_count=state.request_fail_count,
                    cool_down_entry_count=state.cool_down_entry_count,
                    current_cool_down_seconds=state.current_cool_down_seconds,
                    is_in_use=state.is_in_use,
                )
            )
        return states_response

    @with_key_manager_lock
    async def add_key(self, api_key: str) -> str:
        key_identifier = self._get_key_identifier(api_key)
        await self._db_manager.add_key(key_identifier, api_key)
        app_logger.info(f"Added new API key: {key_identifier}")
        return key_identifier

    @with_key_manager_lock
    async def delete_key(self, key_identifier: str):
        await self._db_manager.delete_key(key_identifier)
        app_logger.info(f"Deleted API key: {key_identifier}")

    @with_key_manager_lock
    async def reset_key_state(self, key_identifier: str):
        await self._db_manager.reset_key_state(key_identifier)
        app_logger.info(f"Reset state for API key: {key_identifier}")

    @with_key_manager_lock
    async def reset_all_key_states(self):
        await self._db_manager.reset_all_key_states()
        app_logger.info("Reset state for all API keys.")
