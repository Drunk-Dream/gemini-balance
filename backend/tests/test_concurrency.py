import asyncio

import pytest

from backend.app.core.concurrency import ConcurrencyManager, ConcurrencyTimeoutError
from backend.app.core.config import settings


@pytest.fixture(autouse=True)
def reset_concurrency_settings():
    """
    在每个测试用例之前重置并发设置，以确保测试的独立性。
    """
    original_max_concurrent_requests = settings.MAX_CONCURRENT_REQUESTS
    original_concurrency_timeout_seconds = settings.CONCURRENCY_TIMEOUT_SECONDS
    yield
    settings.MAX_CONCURRENT_REQUESTS = original_max_concurrent_requests
    settings.CONCURRENCY_TIMEOUT_SECONDS = original_concurrency_timeout_seconds


@pytest.mark.asyncio
async def test_concurrency_manager_initialization():
    """
    测试 ConcurrencyManager 的初始化，验证信号量和超时设置是否正确。
    """
    # 确保使用默认设置
    settings.MAX_CONCURRENT_REQUESTS = 5
    settings.CONCURRENCY_TIMEOUT_SECONDS = 10

    manager = ConcurrencyManager()
    assert manager.semaphore._value == settings.MAX_CONCURRENT_REQUESTS
    assert manager._timeout == settings.CONCURRENCY_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_timeout_semaphore_acquire_release_success():
    """
    测试 timeout_semaphore 上下文管理器在正常情况下的获取和释放。
    """
    settings.MAX_CONCURRENT_REQUESTS = 1
    settings.CONCURRENCY_TIMEOUT_SECONDS = 1

    manager = ConcurrencyManager()

    async with manager.timeout_semaphore():
        assert manager.semaphore._value == 0  # 信号量已被获取

    assert manager.semaphore._value == 1  # 信号量已被释放


@pytest.mark.asyncio
async def test_timeout_semaphore_timeout_error():
    """
    测试 timeout_semaphore 上下文管理器在超时情况下的行为。
    """
    settings.MAX_CONCURRENT_REQUESTS = 1
    settings.CONCURRENCY_TIMEOUT_SECONDS = 0.1  # 设置一个很短的超时时间

    manager = ConcurrencyManager()

    # 先获取一个信号量，使后续的获取操作会超时
    await manager.semaphore.acquire()

    with pytest.raises(ConcurrencyTimeoutError, match="获取并发信号量超时。"):
        async with manager.timeout_semaphore():
            pass  # 应该不会执行到这里

    # 确保即使超时，信号量也没有被意外释放（因为 acquire 失败）
    assert manager.semaphore._value == 0
    manager.semaphore.release()  # 释放之前获取的信号量


@pytest.mark.asyncio
async def test_timeout_semaphore_exception_in_context():
    """
    测试 timeout_semaphore 上下管理器在上下文块中发生异常时，信号量是否能正确释放。
    """
    settings.MAX_CONCURRENT_REQUESTS = 1
    settings.CONCURRENCY_TIMEOUT_SECONDS = 1

    manager = ConcurrencyManager()

    class TestException(Exception):
        pass

    with pytest.raises(TestException):
        async with manager.timeout_semaphore():
            assert manager.semaphore._value == 0  # 信号量已被获取
            raise TestException("Something went wrong in the context")

    assert manager.semaphore._value == 1  # 信号量已被释放


@pytest.mark.asyncio
async def test_concurrency_manager_global_instance():
    """
    测试全局 ConcurrencyManager 实例是否正确初始化。
    """
    from backend.app.core.concurrency import concurrency_manager

    # 确保使用默认设置
    settings.MAX_CONCURRENT_REQUESTS = 3
    settings.CONCURRENCY_TIMEOUT_SECONDS = 60

    assert concurrency_manager.semaphore._value == settings.MAX_CONCURRENT_REQUESTS
    assert concurrency_manager._timeout == settings.CONCURRENCY_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_concurrency_manager_acquire_during_sleep():
    """
    测试在第一个信号量获取并await asyncio.sleep()期间，能否继续获取下一个信号量。
    """
    settings.MAX_CONCURRENT_REQUESTS = 2  # 允许两个并发请求
    settings.CONCURRENCY_TIMEOUT_SECONDS = 5

    manager = ConcurrencyManager()

    async def acquire_and_sleep(task_id: int, sleep_time: float):
        async with manager.timeout_semaphore():
            print(f"Task {task_id}: Acquired semaphore.")
            await asyncio.sleep(sleep_time)
            print(f"Task {task_id}: Released semaphore.")
            return True

    # 同时启动两个任务，第一个任务睡眠时间较长，第二个任务睡眠时间较短
    # 预期两个任务都能成功获取信号量
    task1 = acquire_and_sleep(1, 0.5)
    task2 = acquire_and_sleep(2, 0.1)

    results = await asyncio.gather(task1, task2)

    # 验证两个任务都成功获取并释放了信号量
    assert all(results)
    # 验证最终信号量值恢复到最大并发数
    assert manager.semaphore._value == settings.MAX_CONCURRENT_REQUESTS
