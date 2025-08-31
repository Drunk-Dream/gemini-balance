import asyncio

from app.core.config import settings


class ConcurrencyManager:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore


concurrency_manager = ConcurrencyManager()
