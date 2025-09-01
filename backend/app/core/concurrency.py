import asyncio
from contextlib import asynccontextmanager

from backend.app.core.config import settings


class ConcurrencyTimeoutError(Exception):
    """自定义异常，表示并发信号量获取超时。"""

    pass


class ConcurrencyManager:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self._timeout = settings.CONCURRENCY_TIMEOUT_SECONDS

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    @asynccontextmanager
    async def timeout_semaphore(self):
        """
        一个异步上下文管理器，用于在获取信号量时应用超时。
        如果获取信号量超时，则抛出 ConcurrencyTimeoutError。
        """
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._timeout)
            yield
        except asyncio.TimeoutError:
            raise ConcurrencyTimeoutError("获取并发信号量超时。")
        finally:
            if self._semaphore.locked():
                self._semaphore.release()


concurrency_manager = ConcurrencyManager()
