from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Dict, Optional

from backend.app.core.logging import app_logger

if TYPE_CHECKING:
    from backend.app.services.key_managers.db_manager import DBManager

# 全局状态变量
key_manager_lock = asyncio.Lock()
wakeup_event = asyncio.Event()
timeout_tasks: Dict[str, asyncio.Task] = {}
_background_task: Optional[asyncio.Task] = None


async def _release_cooled_down_keys(
    db_manager: DBManager,
    default_check_cooled_down_seconds: int,
    initial_cool_down_seconds: int,
):
    """
    后台任务，定期检查并释放冷却中的密钥。
    """
    while True:
        try:
            releasable_keys = await db_manager.get_releasable_keys()
            for key_identifier in releasable_keys:
                async with key_manager_lock:
                    state = await db_manager.get_key_state(key_identifier)
                    if state and state.cool_down_until <= time.time():
                        state.cool_down_until = 0.0
                        state.request_fail_count = 0
                        state.cool_down_entry_count = 0
                        state.current_cool_down_seconds = initial_cool_down_seconds
                        await db_manager.save_key_state(key_identifier, state)
                        await db_manager.reactivate_key(key_identifier)
                        app_logger.info(f"API key {key_identifier} reactivated.")

            # 获取下一个最近的冷却到期时间戳
            min_cool_down_until = await db_manager.get_min_cool_down_until()

            wait_time = default_check_cooled_down_seconds
            if min_cool_down_until:
                now = time.time()
                # 计算需要等待的秒数，确保不为负
                calculated_wait = max(0, min_cool_down_until - now)
                wait_time = calculated_wait

            wakeup_event.clear()
            # 使用计算出的时间或被事件唤醒
            await asyncio.wait_for(wakeup_event.wait(), timeout=wait_time)
        except asyncio.TimeoutError:
            # 超时是预期的行为，表示我们等待到了下一个检查点
            pass
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            app_logger.info("Background task for releasing cooled down keys cancelled.")
            break
        except Exception as e:
            app_logger.error(f"Error in _release_cooled_down_keys background task: {e}")
            await asyncio.sleep(
                default_check_cooled_down_seconds
            )  # 避免错误导致无限循环


async def timeout_release_key(
    key_identifier: str,
    db_manager: DBManager,
    key_in_use_timeout_seconds: int,
    api_key_failure_threshold: int,
):
    """
    在指定超时后释放密钥，并增加失败计数。
    """
    try:
        await asyncio.sleep(key_in_use_timeout_seconds)
        async with key_manager_lock:
            state = await db_manager.get_key_state(key_identifier)
            if state and state.is_in_use:  # 再次检查密钥是否仍在使用中
                state.request_fail_count += 1
                # 如果失败次数达到阈值，则进入冷却
                if state.request_fail_count >= api_key_failure_threshold:
                    # 这里不直接进入冷却，只增加失败计数，由mark_key_fail处理冷却逻辑
                    pass
                await db_manager.save_key_state(key_identifier, state)
                await db_manager.release_key_from_use(key_identifier)
                app_logger.warning(
                    f"Key {key_identifier} released from use due to timeout. "
                    f"Failure count increased to {state.request_fail_count}."
                )
    except asyncio.CancelledError:
        app_logger.debug(f"Timeout task for key {key_identifier} was cancelled.")
    except Exception as e:
        app_logger.error(f"Error in timeout_release_key for {key_identifier}: {e}")
    finally:
        # 无论任务是否完成或取消，都从字典中移除
        if key_identifier in timeout_tasks:
            del timeout_tasks[key_identifier]


async def initialize_key_states(db_manager: DBManager):
    """
    应用启动时初始化密钥状态，释放所有处于“使用中”状态的密钥。
    """
    async with key_manager_lock:
        keys_in_use = await db_manager.get_keys_in_use()
        for key in keys_in_use:
            app_logger.warning(f"Releasing {key} from use due to initialization.")
            await db_manager.release_key_from_use(key)
        app_logger.info("Key states initialized: all 'in_use' keys released.")


async def start_background_task(
    db_manager: DBManager,
    default_check_cooled_down_seconds: int,
    initial_cool_down_seconds: int,
):
    """
    启动后台任务，用于定期释放冷却中的密钥。
    """
    global _background_task
    if _background_task is None or _background_task.done():
        app_logger.info("Starting background task for releasing cooled down keys.")
        _background_task = asyncio.create_task(
            _release_cooled_down_keys(
                db_manager, default_check_cooled_down_seconds, initial_cool_down_seconds
            )
        )


def stop_background_task():
    """
    停止后台任务。
    """
    global _background_task
    if _background_task:
        app_logger.info("Stopping background task for releasing cooled down keys.")
        _background_task.cancel()
        _background_task = None
    # 取消所有未完成的超时任务
    for key_identifier, task in list(timeout_tasks.items()):
        if not task.done():
            task.cancel()
            app_logger.debug(f"Cancelled timeout task for key {key_identifier}.")
        del timeout_tasks[key_identifier]
    app_logger.info("All timeout tasks cancelled.")
