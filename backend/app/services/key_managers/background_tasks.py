from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Dict,
    Optional,
    ParamSpec,
    TypeVar,
)

import httpx

from backend.app.core.config import settings
from backend.app.core.errors import ErrorType
from backend.app.core.logging import app_logger

if TYPE_CHECKING:
    from backend.app.services.chat_service.base_service import RequestInfo
    from backend.app.services.key_managers.db_manager import DBManager
    from backend.app.services.key_managers.key_state_manager import KeyStateManager

_P = ParamSpec("_P")
_R = TypeVar("_R")


class BackgroundTaskManager:
    _instance: Optional["BackgroundTaskManager"] = None

    def __init__(self) -> None:
        if BackgroundTaskManager._instance is not None:
            raise RuntimeError(
                "BackgroundTaskManager is a singleton and already instantiated."
            )

        self.key_manager_lock = asyncio.Lock()
        self.wakeup_event = asyncio.Event()
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self._background_task: Optional[asyncio.Task] = None
        BackgroundTaskManager._instance = self

    @classmethod
    def get_instance(cls) -> "BackgroundTaskManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _release_cooled_down_keys(
        self,
        db_manager: DBManager,
    ):
        """
        后台任务，定期检查并释放冷却中的密钥。
        """
        while True:
            app_logger.debug("Background task for releasing cooled down keys started.")
            try:
                releasable_keys = await db_manager.get_releasable_keys()
                for key_identifier in releasable_keys:
                    async with self.key_manager_lock:
                        state = await db_manager.get_key_state(key_identifier)
                        if (
                            state
                            and state.cool_down_until <= time.time()
                            and self.check_key_health(key_identifier, db_manager)
                        ):
                            await db_manager.reactivate_key(key_identifier)
                            app_logger.info(f"API key {key_identifier} reactivated.")

                min_cool_down_until = await db_manager.get_min_cool_down_until()

                wait_time = settings.DEFAULT_CHECK_COOLED_DOWN_SECONDS
                if min_cool_down_until:
                    now = time.time()
                    calculated_wait = max(0, min_cool_down_until - now)
                    wait_time = calculated_wait

                self.wakeup_event.clear()
                await asyncio.wait_for(self.wakeup_event.wait(), timeout=wait_time)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                app_logger.info(
                    "Background task for releasing cooled down keys cancelled."
                )
                break
            except Exception as e:
                app_logger.error(
                    f"Error in _release_cooled_down_keys background task: {e}"
                )
                await asyncio.sleep(settings.DEFAULT_CHECK_COOLED_DOWN_SECONDS)

    async def check_key_health(
        self, key_identifier: str, db_manager: DBManager
    ) -> bool:
        """
        检查密钥的健康状况，如果健康再从冷却中释放
        """
        if not settings.CHECK_HEALTH_AFTER_COOL_DOWN:
            return True
        client = httpx.AsyncClient(
            base_url=settings.GEMINI_API_BASE_URL,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
        )
        api_key = await db_manager.get_key_from_identifier(key_identifier)
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        body = {"contents": [{"parts": [{"text": "Hello, world!"}]}]}
        try:
            async with client:
                response = await client.post(
                    url="models/gemini-2.5-flash-lite:generateContent",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            app_logger.error(f"Error checking key health for {key_identifier}: {e}")
            return False

        return True

    async def _timeout_release_key(
        self,
        key_identifier: str,
        key_in_use_timeout_seconds: int,
        request_info: RequestInfo,
        key_manager: KeyStateManager,
    ):
        """
        在指定超时后释放密钥，并增加失败计数。
        """
        try:
            await asyncio.sleep(key_in_use_timeout_seconds)
            await key_manager.mark_key_fail(
                key_identifier, ErrorType.USE_TIMEOUT_ERROR, request_info
            )
        except asyncio.CancelledError:
            app_logger.debug(f"Timeout task for key {key_identifier} was cancelled.")
        except Exception as e:
            app_logger.error(f"Error in _timeout_release_key for {key_identifier}: {e}")
        finally:
            if key_identifier in self.timeout_tasks:
                del self.timeout_tasks[key_identifier]

    def create_timeout_task(
        self,
        key_identifier: str,
        key_in_use_timeout_seconds: int,
        request_info: RequestInfo,
        key_manager: KeyStateManager,
    ):
        """
        创建并启动一个用于超时释放密钥的任务。
        """
        if key_identifier in self.timeout_tasks:
            self.timeout_tasks[key_identifier].cancel()

        task = asyncio.create_task(
            self._timeout_release_key(
                key_identifier,
                key_in_use_timeout_seconds,
                request_info,
                key_manager,
            )
        )
        self.timeout_tasks[key_identifier] = task

    def cancel_timeout_task(self, key_identifier: str):
        """
        取消指定密钥的超时任务。
        """
        if key_identifier in self.timeout_tasks:
            task = self.timeout_tasks.pop(key_identifier)
            if not task.done():
                task.cancel()
                app_logger.debug(f"Cancelled timeout task for key {key_identifier}.")

    async def initialize_key_states(self, db_manager: DBManager):
        """
        应用启动时初始化密钥状态，释放所有处于“使用中”状态的密钥。
        """
        async with self.key_manager_lock:
            keys_in_use = await db_manager.get_keys_in_use()
            for key in keys_in_use:
                app_logger.warning(f"Releasing {key} from use due to initialization.")
                await db_manager.release_key_from_use(key)
            app_logger.info("Key states initialized: all 'in_use' keys released.")

    async def start_background_task(
        self,
        db_manager: DBManager,
    ):
        """
        启动后台任务，用于定期释放冷却中的密钥。
        """
        if self._background_task is None or self._background_task.done():
            app_logger.info("Starting background task for releasing cooled down keys.")
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys(
                    db_manager,
                )
            )

    def stop_background_task(self):
        """
        停止后台任务。
        """
        if self._background_task:
            app_logger.info("Stopping background task for releasing cooled down keys.")
            self._background_task.cancel()
            self._background_task = None

        for key_identifier, task in list(self.timeout_tasks.items()):
            if not task.done():
                task.cancel()
                app_logger.debug(f"Cancelled timeout task for key {key_identifier}.")
            del self.timeout_tasks[key_identifier]
        app_logger.info("All timeout tasks cancelled.")


# 获取单例实例
background_task_manager = BackgroundTaskManager.get_instance()


def get_background_task_manager():
    return background_task_manager


def with_key_manager_lock(
    func: Callable[_P, Awaitable[_R]],
) -> Callable[_P, Awaitable[_R]]:
    """
    一个异步装饰器，用于在执行函数时获取 key_manager_lock。
    """

    @wraps(func)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        async with background_task_manager.key_manager_lock:
            return await func(*args, **kwargs)

    return wrapper
