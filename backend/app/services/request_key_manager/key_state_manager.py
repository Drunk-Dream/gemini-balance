from __future__ import annotations

import asyncio  # 导入 asyncio
import time
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    ParamSpec,
    TypeVar,
)

from fastapi import Depends

from backend.app.api.api.schemas.request_keys import KeyStatus, KeyStatusResponse
from backend.app.core.config import get_settings
from backend.app.core.errors import ErrorType
from backend.app.core.logging import app_logger
from backend.app.services.request_key_manager.db_manager import DBManager, KeyType
from backend.app.services.request_key_manager.sqlite_manager import SQLiteDBManager

if TYPE_CHECKING:
    from backend.app.core.config import Settings
    from backend.app.services.request_key_manager.schemas import KeyState

_P = ParamSpec("_P")
_R = TypeVar("_R")

# 在模块级别创建全局锁
key_manager_lock = asyncio.Lock()


def get_key_db_manager(
    settings: Settings = Depends(get_settings),
) -> DBManager:
    if settings.DATABASE_TYPE == "sqlite":
        db_manager = SQLiteDBManager(settings)
    else:
        raise ValueError(f"Unsupported key manager type: {settings.DATABASE_TYPE}")
    return db_manager


def with_key_manager_lock(
    func: Callable[_P, Awaitable[_R]],
) -> Callable[_P, Awaitable[_R]]:
    """
    一个异步装饰器，用于在执行函数时获取 key_manager_lock。
    """

    @wraps(func)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        async with key_manager_lock:
            return await func(*args, **kwargs)

    return wrapper


class KeyStateManager:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        db_manager: DBManager = Depends(get_key_db_manager),
    ):
        self._initial_cool_down_seconds = settings.API_KEY_COOL_DOWN_SECONDS
        self._api_key_failure_threshold = settings.API_KEY_FAILURE_THRESHOLD
        self._max_cool_down_seconds = settings.MAX_COOL_DOWN_SECONDS
        self._db_manager = db_manager

    def _get_key_identifier(self, key: str) -> str:
        """生成一个对日志友好且唯一的密钥标识符"""
        import hashlib

        return f"key_sha256_{hashlib.sha256(key.encode()).hexdigest()[:8]}"

    def _calculate_cool_down_seconds(self, state: KeyState) -> int:
        return min(
            self._initial_cool_down_seconds * (2**state.cool_down_entry_count),
            self._max_cool_down_seconds,
        )

    # --------------- Key Management ---------------
    @with_key_manager_lock
    async def add_key(self, api_key: str) -> str:
        key_identifier = self._get_key_identifier(api_key)
        key = KeyType(
            identifier=key_identifier,
            brief=DBManager.key_to_brief(api_key),
            full=api_key,
        )
        await self._db_manager.add_key(key)
        app_logger.info(f"Added new API key: {key.brief}")
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

    # --------------- Get Key State ---------------
    @with_key_manager_lock
    async def get_key_state(self, key_identifier: str) -> KeyState | None:
        return await self._db_manager.get_key_state(key_identifier)

    @with_key_manager_lock
    async def get_all_key_status(self) -> KeyStatusResponse:
        states_response: List[KeyStatus] = []
        now = time.time()
        states = await self._db_manager.get_all_key_states()

        for state in states:
            key_identifier = state.key_identifier
            key_brief = self._db_manager.key_to_brief(state.api_key)
            cool_down_remaining = max(0, state.cool_down_until - now)

            if state.is_in_use:
                status = "in_use"
            elif state.is_cooled_down:
                status = "cooling_down"
            else:
                status = "active"

            states_response.append(
                KeyStatus(
                    key_identifier=key_identifier,
                    key_brief=key_brief,
                    status=status,
                    cool_down_seconds_remaining=round(cool_down_remaining),
                    failure_count=state.request_fail_count,
                    cool_down_entry_count=state.cool_down_entry_count,
                    current_cool_down_seconds=self._calculate_cool_down_seconds(state),
                )
            )

        key_counts = await self._db_manager.get_key_counts()
        return KeyStatusResponse(
            keys=states_response,
            total_keys_count=key_counts.total,
            in_use_keys_count=key_counts.in_use,
            cooled_down_keys_count=key_counts.cooled_down,
            available_keys_count=key_counts.available,
        )

    @with_key_manager_lock
    async def get_next_key(self) -> Optional[KeyType]:
        key = await self._db_manager.get_and_lock_next_available_key()
        if not key:
            return None
        return key

    @with_key_manager_lock
    async def get_releasable_keys(self) -> List[KeyType]:
        return await self._db_manager.get_releasable_keys()

    @with_key_manager_lock
    async def get_keys_in_use(self) -> List[KeyType]:
        return await self._db_manager.get_keys_in_use()

    @with_key_manager_lock
    async def get_available_keys_count(self) -> int:
        counts = await self._db_manager.get_key_counts()
        return counts.available

    @with_key_manager_lock
    async def get_min_cool_down_until(self) -> float | None:
        return await self._db_manager.get_min_cool_down_until()

    @with_key_manager_lock
    async def get_key_identifier_to_brief_dict(self) -> Dict[str, str]:
        """获取所有key的key_identifier到brief的映射"""
        states = await self._db_manager.get_all_key_states()
        if not states:
            return {}
        return {
            state.key_identifier: DBManager.key_to_brief(state.api_key)
            for state in states
        }

    # --------------- Change Key State ---------------
    @with_key_manager_lock
    async def mark_key_fail(self, key: KeyType, error_type: ErrorType):
        error_type_str = error_type.value
        state = await self._db_manager.get_key_state(key.identifier)
        if not state:
            return False

        state.request_fail_count += 1
        state.last_usage_time = time.time()
        state.is_in_use = False  # 失败后释放

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
            state.is_cooled_down = True
            app_logger.warning(
                f"Key {key.brief} cooled down for "
                f"{current_cool_down_seconds:.2f}s due to {error_type_str}."
            )
        else:
            app_logger.info(
                f"Key {key.brief} released from "
                f"use after {error_type_str} without cooldown."
            )

        await self._db_manager.save_key_state(state)
        return should_cool_down

    @with_key_manager_lock
    async def mark_key_success(
        self,
        key: KeyType,
    ):
        state = await self._db_manager.get_key_state(key.identifier)
        if not state:
            return
        state.cool_down_entry_count = 0
        state.request_fail_count = 0
        state.last_usage_time = time.time()
        state.is_in_use = False
        state.is_cooled_down = False

        await self._db_manager.save_key_state(state)

    @with_key_manager_lock
    async def reactivate_key(self, key: KeyType):
        state = await self._db_manager.get_key_state(key.identifier)
        if not state:
            return
        state.is_cooled_down = False
        state.is_in_use = False
        state.request_fail_count = 0
        await self._db_manager.save_key_state(state)

    @with_key_manager_lock
    async def release_key_from_use(self, key: KeyType):
        state = await self._db_manager.get_key_state(key.identifier)
        if not state:
            return
        state.is_in_use = False
        await self._db_manager.save_key_state(state)
