import functools
import inspect
import logging
from typing import Awaitable, Callable, ParamSpec, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")


def log_function_calls(
    logger: logging.Logger,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    一个用于记录函数调用开始、结束和异常的装饰器。
    支持同步和异步函数。

    Args:
        logger: 用于记录日志的 logger 实例。
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            func_name = func.__name__
            logger.info(f"正在调用 {func_name}...")
            try:
                # 明确地将 func 转换为 Awaitable，以帮助类型检查器
                result = await cast(Awaitable[R], func(*args, **kwargs))
                logger.debug(f"{func_name} 执行完毕。")
                return result
            except Exception as e:
                logger.error(f"调用 {func_name} 时发生错误: {e}", exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            func_name = func.__name__
            logger.info(f"正在调用 {func_name}...")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} 执行完毕。")
                return result
            except Exception as e:
                logger.error(f"调用 {func_name} 时发生错误: {e}", exc_info=True)
                raise

        if inspect.iscoroutinefunction(func):
            # 对于异步函数，返回异步包装器
            return cast(Callable[P, R], async_wrapper)
        else:
            # 对于同步函数，返回同步包装器
            return cast(Callable[P, R], sync_wrapper)

    return decorator
