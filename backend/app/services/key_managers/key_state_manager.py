from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends
from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.core.errors import ErrorType
from backend.app.core.logging import app_logger
from backend.app.services.key_managers.background_tasks import (
    background_task_manager,
    with_key_manager_lock,
)
from backend.app.services.key_managers.sqlite_manager import SQLiteDBManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.schemas import RequestLog

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.chat_service.types import RequestInfo
    from backend.app.services.key_managers.db_manager import (
        DBManager,
        KeyState,
        KeyType,
    )


class KeyStatusResponse(BaseModel):
    key_identifier: str
    key_brief: str
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

    def _calculate_cool_down_seconds(self, state: KeyState) -> int:
        return min(
            self._initial_cool_down_seconds * (2**state.cool_down_entry_count),
            self._max_cool_down_seconds,
        )

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

    @with_key_manager_lock
    async def get_next_key(self, request_info: RequestInfo) -> Optional[KeyType]:
        key = await self._db_manager.get_next_available_key()
        if not key:
            return None
        await self._db_manager.move_to_use(key.identifier)
        # 启动一个定时任务，在超时后自动释放密钥
        self._background_task_manager.create_timeout_task(
            key,
            self._key_in_use_timeout_seconds,
            request_info,
            self,
        )
        return key

    @with_key_manager_lock
    async def mark_key_fail(
        self, key: KeyType, error_type: ErrorType, request_info: RequestInfo
    ):
        # 取消对应的超时任务
        if error_type != ErrorType.USE_TIMEOUT_ERROR:
            self._background_task_manager.cancel_timeout_task(key)

        error_type_str = error_type.value
        state = await self._db_manager.get_key_state(key)
        if not state:
            return

        state.request_fail_count += 1
        state.last_usage_time = time.time()

        should_cool_down = error_type.should_cool_down

        if (
            not should_cool_down
            and state.request_fail_count >= self._api_key_failure_threshold
        ):
            should_cool_down = True
            error_type_str += " & max_failures_error"  # 保持原始字符串，以便日志记录

        if should_cool_down:
            current_cool_down_seconds = self._calculate_cool_down_seconds(state)
            state.current_cool_down_seconds = current_cool_down_seconds
            state.cool_down_entry_count += 1
            state.cool_down_until = time.time() + current_cool_down_seconds
            await self._db_manager.move_to_cooldown(
                key.identifier, state.cool_down_until
            )
            self._background_task_manager.wakeup_event.set()
            app_logger.warning(
                f"[Request ID: {request_info.request_id}] Key {key.brief} cooled down for "
                f"{current_cool_down_seconds:.2f}s due to {error_type_str}."
            )
        else:  # 如果不需要冷却，则释放密钥
            await self._db_manager.release_key_from_use(key)
            app_logger.info(
                f"[Request ID: {request_info.request_id}] Key {key.identifier} released from "
                f"use after {error_type_str} without cooldown."
            )

        await self._db_manager.save_key_state(key, state)

        # 记录请求日志
        log_entry = RequestLog(
            id=None,
            request_id=request_info.request_id,
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key.identifier,
            auth_key_alias=request_info.auth_key_alias,
            model_name=request_info.model_id,
            is_success=False,
            error_type=error_type_str,
        )
        await self._request_log_manager.record_request_log(log_entry)

    @with_key_manager_lock
    async def mark_key_success(
        self,
        key: KeyType,
        request_info: RequestInfo,
    ):
        # 取消对应的超时任务
        self._background_task_manager.cancel_timeout_task(key)

        state = await self._db_manager.get_key_state(key)
        if not state:
            return
        state.cool_down_entry_count = 0
        state.request_fail_count = 0
        state.last_usage_time = time.time()

        await self._db_manager.save_key_state(key, state)
        await self._db_manager.reactivate_key(key)

        # 记录请求日志
        log_entry = RequestLog(
            id=None,
            request_id=request_info.request_id,
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key.identifier,
            auth_key_alias=request_info.auth_key_alias,
            model_name=request_info.model_id,
            is_success=True,
            prompt_tokens=request_info.prompt_tokens,
            completion_tokens=request_info.completion_tokens,
            total_tokens=request_info.total_tokens,
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
        states = await self._db_manager.get_all_key_states()

        for state in states:
            key_identifier = state.key_identifier
            key_brief = self._db_manager.key_to_brief(state.api_key)
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
                    key_brief=key_brief,
                    status=status,
                    cool_down_seconds_remaining=round(cool_down_remaining, 2),
                    daily_usage=key_daily_usage,
                    failure_count=state.request_fail_count,
                    cool_down_entry_count=state.cool_down_entry_count,
                    current_cool_down_seconds=self._calculate_cool_down_seconds(state),
                    is_in_use=state.is_in_use,
                )
            )
        return states_response

    @with_key_manager_lock
    async def get_available_keys_count(self) -> int:
        counts = await self._db_manager.get_available_keys_count()
        return counts

    @with_key_manager_lock
    async def get_releasable_keys(self) -> List[KeyType]:
        return await self._db_manager.get_releasable_keys()

    @with_key_manager_lock
    async def get_key_state(self, key: KeyType) -> KeyState | None:
        return await self._db_manager.get_key_state(key)

    @with_key_manager_lock
    async def get_min_cool_down_until(self) -> float | None:
        return await self._db_manager.get_min_cool_down_until()

    @with_key_manager_lock
    async def reactivate_key(self, key: KeyType):
        await self._db_manager.reactivate_key(key)

    @with_key_manager_lock
    async def get_keys_in_use(self) -> List[KeyType]:
        return await self._db_manager.get_keys_in_use()

    @with_key_manager_lock
    async def release_key_from_use(self, key: KeyType):
        await self._db_manager.release_key_from_use(key)
