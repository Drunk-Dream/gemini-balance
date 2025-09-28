from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional

from fastapi import Request

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class ConcurrencyTimeoutError(Exception):
    """自定义异常，表示并发信号量获取超时。"""

    pass


class ConcurrencyManager:
    _instance: Optional["ConcurrencyManager"] = None

    def __init__(self, settings: Settings):
        if ConcurrencyManager._instance is not None:
            raise RuntimeError(
                "ConcurrencyManager is a singleton and already instantiated."
            )

        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self._timeout = settings.CONCURRENCY_TIMEOUT_SECONDS
        ConcurrencyManager._instance = self

    @classmethod
    def get_instance(cls, settings: Settings) -> "ConcurrencyManager":
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    @asynccontextmanager
    async def timeout_semaphore(self):
        """
        一个异步上下文管理器，用于在获取信号量时应用超时。
        如果获取信号量超时，则抛出 ConcurrencyTimeoutError。
        """
        acquired = False  # 新增标志，表示信号量是否被成功获取
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._timeout)
            acquired = True  # 成功获取信号量后设置为 True
            yield
        except asyncio.TimeoutError:
            raise ConcurrencyTimeoutError("获取并发信号量超时。")
        finally:
            if acquired:  # 只有在成功获取信号量后才释放
                self._semaphore.release()


def get_concurrency_manager(request: Request) -> ConcurrencyManager:
    return request.app.state.concurrency_manager
