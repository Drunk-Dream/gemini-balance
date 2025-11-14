import asyncio
import time
from typing import Dict, Optional

import httpx
from fastapi import Request

from backend.app.core.config import Settings
from backend.app.core.errors import ErrorType
from backend.app.core.logging import app_logger
from backend.app.services.request_key_manager.key_state_manager import (
    KeyStateManager,
    get_key_db_manager,
)
from backend.app.services.request_key_manager.schemas import ApiKey


class BackgroundTaskManager:
    _instance: Optional["BackgroundTaskManager"] = None

    def __init__(self, settings: Settings) -> None:
        if BackgroundTaskManager._instance is not None:
            raise RuntimeError(
                "BackgroundTaskManager is a singleton and already instantiated."
            )
        self._key_manager: KeyStateManager = KeyStateManager(
            settings, get_key_db_manager(settings)
        )
        self._check_health_after_cool_down = settings.CHECK_HEALTH_AFTER_COOL_DOWN
        self._check_health_time_interval_seconds = (
            settings.CHECK_HEALTH_TIME_INTERVAL_SECONDS
        )
        self._default_check_cooled_down_seconds = (
            settings.DEFAULT_CHECK_COOLED_DOWN_SECONDS
        )
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS
        self._gemini_api_base_url = settings.GEMINI_API_BASE_URL
        self._request_timeout_seconds = settings.REQUEST_TIMEOUT_SECONDS
        self._http_client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._gemini_api_base_url,
            timeout=httpx.Timeout(self._request_timeout_seconds),
        )

        self.wakeup_release_cool_down_event = asyncio.Event()
        self.wakeup_release_in_use_event = asyncio.Event()
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self._background_task: Optional[asyncio.Task] = None
        self._release_in_use_background_task: Optional[asyncio.Task] = None
        BackgroundTaskManager._instance = self

    @classmethod
    def get_instance(cls, settings: Settings) -> "BackgroundTaskManager":
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    # --------------- Release Key From Cool Down ---------------
    async def _release_cooled_down_keys(self):
        """
        后台任务，定期检查并释放冷却中的密钥。
        """
        while True:
            app_logger.debug("Background task for releasing cooled down keys started.")
            try:
                releasable_keys = await self._key_manager.get_releasable_keys()
                for key in releasable_keys:
                    state = await self._key_manager.get_key_state(key.identifier)
                    if (
                        state
                        and state.cool_down_until <= time.time()
                        and await self._check_key_health(key)
                    ):
                        await self._key_manager.reactivate_key(key)
                        app_logger.info(f"API key {key.brief} reactivated.")

                min_cool_down_until = await self._key_manager.get_min_cool_down_until()

                if min_cool_down_until:
                    now = time.time()
                    calculated_wait = max(0.1, min_cool_down_until - now)
                    wait_time = calculated_wait
                else:
                    wait_time = self._default_check_cooled_down_seconds

                # 如果开启了健康检查，确保检查频率不低于设置的时间间隔
                if self._check_health_after_cool_down:
                    wait_time = min(wait_time, self._check_health_time_interval_seconds)

                self.wakeup_release_cool_down_event.clear()
                await asyncio.wait_for(
                    self.wakeup_release_cool_down_event.wait(), timeout=wait_time
                )
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
                await asyncio.sleep(self._default_check_cooled_down_seconds)

    async def _check_key_health(self, key: ApiKey) -> bool:
        """
        检查密钥的健康状况，如果健康再从冷却中释放
        """
        if not self._check_health_after_cool_down:
            app_logger.debug(f"Skipping {key.brief} health check.")
            return True
        app_logger.debug(f"Checking {key.brief} health.")

        headers = {"Content-Type": "application/json", "x-goog-api-key": key.full}
        body = {"contents": [{"parts": [{"text": "Hello, world!"}]}]}
        try:
            response = await self._http_client.post(
                url="/v1beta/models/gemini-2.5-flash-lite:generateContent",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            app_logger.info(f"Key {key.brief} is healthy.")
            return True
        except Exception as e:
            await self._key_manager.mark_key_fail(key, ErrorType.HEALTH_CHECK_ERROR)
            app_logger.error(f"Error checking key health for {key.brief}: {e}")
            return False

    # --------------- Release Key From Use ---------------
    async def initialize_key_states(self):
        """
        应用启动时初始化密钥状态，释放所有处于“使用中”状态的密钥。
        """
        keys_in_use = await self._key_manager.get_keys_in_use()
        for key in keys_in_use:
            app_logger.warning(f"Releasing {key.brief} from use due to initialization.")
            await self._key_manager.release_key_from_use(key)
        app_logger.info("Key states initialized: all 'in_use' keys released.")

    async def _release_key_from_use(self):
        """
        后台任务，定期检查并释放未被在is_in_use中释放的key。
        NOTE: 目前猜测可能的原因是在请求期间取消任务，导致fastapi把任务取消，进而
        key_state_manager中的release_key_from_use未被成功调用(可能是异步调用的原因)
        针对这种情况，新建一个后台任务，定期检查key in use并释放
        """
        while True:
            app_logger.debug("Background task for releasing key in use started.")
            try:
                wait_time = self._default_check_cooled_down_seconds
                keys_in_use = await self._key_manager.get_keys_in_use()
                for key in keys_in_use:
                    state = await self._key_manager.get_key_state(key.identifier)
                    if not state:
                        continue
                    now = time.time()
                    locked_until = (
                        state.last_usage_time + self._key_in_use_timeout_seconds
                    )
                    if locked_until <= now:
                        await self._key_manager.release_key_from_use(key)
                        app_logger.warning(
                            f"Releasing {key.brief} from use due to timeout."
                        )
                    else:
                        wait_time = min(wait_time, max(locked_until - now, 1))
                self.wakeup_release_in_use_event.clear()
                await asyncio.wait_for(
                    self.wakeup_release_in_use_event.wait(), wait_time
                )
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                app_logger.info("Background task for releasing keys in use cancelled.")
                break
            except Exception as e:
                app_logger.error(f"Error occurred while releasing keys from use: {e}")

    async def _timeout_release_key(
        self,
        key: ApiKey,
        key_in_use_timeout_seconds: int,
    ):
        """
        在指定超时后释放密钥，并增加失败计数。
        """
        try:
            await asyncio.sleep(key_in_use_timeout_seconds)
            await self._key_manager.mark_key_fail(key, ErrorType.USE_TIMEOUT_ERROR)
        except asyncio.CancelledError:
            app_logger.debug(f"Timeout task for key {key.brief} was cancelled.")
        except Exception as e:
            app_logger.error(f"Error in _timeout_release_key for {key.brief}: {e}")
        finally:
            if key.identifier in self.timeout_tasks:
                del self.timeout_tasks[key.identifier]

    def create_timeout_task(
        self,
        key: ApiKey,
        key_in_use_timeout_seconds: int,
    ):
        """
        创建并启动一个用于超时释放密钥的任务。
        """
        if key.identifier in self.timeout_tasks:
            self.timeout_tasks[key.identifier].cancel()

        task = asyncio.create_task(
            self._timeout_release_key(
                key,
                key_in_use_timeout_seconds,
            )
        )
        self.timeout_tasks[key.identifier] = task

    def cancel_timeout_task(self, key: ApiKey):
        """
        取消指定密钥的超时任务。
        """
        if key.identifier in self.timeout_tasks:
            task = self.timeout_tasks.pop(key.identifier)
            if not task.done():
                task.cancel()
                app_logger.debug(f"Cancelled timeout task for key {key.brief}.")

    async def _close_http_client(self):
        if self._http_client:
            await self._http_client.aclose()
            app_logger.info("HTTP client closed.")

    # --------------- Start and Stop Background Tasks ---------------
    async def start_background_task(self):
        """
        启动后台任务，用于定期释放冷却中的密钥和检查使用中的密钥。
        """
        if self._background_task is None or self._background_task.done():
            app_logger.info("Starting background task for releasing cooled down keys.")
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )

        if (
            self._release_in_use_background_task is None
            or self._release_in_use_background_task.done()
        ):
            app_logger.info("Starting background task for releasing keys from use.")
            self._release_in_use_background_task = asyncio.create_task(
                self._release_key_from_use()
            )

    async def stop_background_task(self):
        """
        停止后台任务。
        """
        if self._background_task:
            app_logger.info("Stopping background task for releasing cooled down keys.")
            self._background_task.cancel()
            self._background_task = None

        if self._release_in_use_background_task:
            app_logger.info("Stopping background task for releasing keys from use.")
            self._release_in_use_background_task.cancel()
            self._release_in_use_background_task = None

        for key_identifier, task in list(self.timeout_tasks.items()):
            if not task.done():
                task.cancel()
                app_logger.debug(f"Cancelled timeout task for key {key_identifier}.")
            del self.timeout_tasks[key_identifier]
        app_logger.info("All timeout tasks cancelled.")
        await self._close_http_client()


def get_background_task_manager(request: Request) -> BackgroundTaskManager:
    return request.app.state.background_task_manager
