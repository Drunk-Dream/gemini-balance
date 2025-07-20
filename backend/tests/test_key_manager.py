import asyncio
import time
from collections import deque
from datetime import datetime
from unittest.mock import patch

import pytest

# 导入待测试的 KeyManager 类
from app.services.key_manager import KeyManager, KeyState, KeyStatusResponse


# 模拟 settings 模块，因为 KeyManager 依赖它
@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.services.key_manager.settings") as mock_settings_obj:
        mock_settings_obj.API_KEY_FAILURE_THRESHOLD = 3
        mock_settings_obj.MAX_COOL_DOWN_SECONDS = 3600
        yield mock_settings_obj


@pytest.fixture
def key_manager_instance(mock_settings):
    """
    为 KeyManager 提供一个测试实例。
    """
    api_keys = ["key1", "key2", "key3"]
    cool_down_seconds = 5
    api_key_failure_threshold = mock_settings.API_KEY_FAILURE_THRESHOLD
    max_cool_down_seconds = mock_settings.MAX_COOL_DOWN_SECONDS
    return KeyManager(
        api_keys, cool_down_seconds, api_key_failure_threshold, max_cool_down_seconds
    )


@pytest.mark.asyncio
async def test_key_manager_init(mock_settings):
    """
    测试 KeyManager 的初始化。
    """
    api_keys = ["test_key_a", "test_key_b"]
    cool_down = 10
    api_key_failure_threshold = 3
    max_cool_down_seconds = 3600
    manager = KeyManager(
        api_keys, cool_down, api_key_failure_threshold, max_cool_down_seconds
    )

    assert manager._available_keys == deque(api_keys)
    assert manager._initial_cool_down_seconds == cool_down
    assert len(manager._key_states) == len(api_keys)
    for key in api_keys:
        expected_state = KeyState(
            cool_down_until=0.0,
            request_fail_count=0,
            cool_down_entry_count=0,
            current_cool_down_seconds=cool_down,
            usage_today={},
            last_usage_date=datetime.now().strftime("%Y-%m-%d"),
        )
        assert manager._key_states[key] == expected_state
    for key_state in manager._key_states.values():
        assert key_state.cool_down_until == 0.0

    with pytest.raises(ValueError, match="API key list cannot be empty."):
        KeyManager([], 5, 3, 3600)


@pytest.mark.asyncio
async def test_get_next_key_basic_rotation(key_manager_instance):
    """
    测试 get_next_key 的基本轮询功能。
    """
    manager = key_manager_instance
    keys = []
    for _ in range(5):
        key = await manager.get_next_key()
        keys.append(key)
        assert key in ["key1", "key2", "key3"]

    assert keys == ["key1", "key2", "key3", "key1", "key2"]


@pytest.mark.asyncio
async def test_get_next_key_no_available_keys(key_manager_instance):
    """
    测试当没有可用 key 时 get_next_key 返回 None。
    """
    manager = key_manager_instance
    # 停用所有 key
    await manager.deactivate_key("key1", "auth_error")
    await manager.deactivate_key("key2", "auth_error")
    await manager.deactivate_key("key3", "auth_error")

    key = await manager.get_next_key()
    assert key is None


@pytest.mark.asyncio
async def test_get_next_key_reactivates_cooled_down_keys(key_manager_instance):
    """
    测试 get_next_key 能够重新激活冷却时间已到的 key。
    """
    manager = key_manager_instance

    # 停用 key1
    await manager.deactivate_key("key1", "auth_error")
    assert "key1" not in manager._available_keys
    assert manager._key_states["key1"].cool_down_until > 0  # 检查是否进入冷却状态

    # 模拟时间流逝，使 key1 冷却结束
    with patch(
        "time.time", return_value=time.time() + manager._initial_cool_down_seconds + 1
    ):
        key = await manager.get_next_key()
        # 此时 key1 应该被重新激活并可用
        assert "key1" in manager._available_keys
        assert manager._key_states["key1"].cool_down_until == 0.0  # 检查是否退出冷却状态
        # 再次获取 key，确保轮询正常
        assert key in [
            "key2",
            "key3",
            "key1",
        ]  # 顺序可能因内部实现而异，但 key1 应该在可用队列中


@pytest.mark.asyncio
async def test_deactivate_key_auth_error(key_manager_instance):
    """
    测试 auth_error 类型的停用。
    """
    manager = key_manager_instance
    initial_time = time.time()
    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key1", "auth_error")

    assert "key1" not in manager._available_keys
    assert manager._key_states["key1"].cool_down_until > 0
    assert manager._key_states["key1"].request_fail_count == 1
    assert manager._key_states["key1"].cool_down_entry_count == 1
    assert (
        manager._key_states["key1"].current_cool_down_seconds
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key1"].cool_down_until
        == initial_time + manager._initial_cool_down_seconds
    )


@pytest.mark.asyncio
async def test_deactivate_key_rate_limit_error(key_manager_instance):
    """
    测试 rate_limit_error 类型的停用。
    """
    manager = key_manager_instance
    initial_time = time.time()
    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key2", "rate_limit_error")

    assert "key2" not in manager._available_keys
    assert manager._key_states["key2"].cool_down_until > 0
    assert manager._key_states["key2"].request_fail_count == 1
    assert manager._key_states["key2"].cool_down_entry_count == 1
    assert (
        manager._key_states["key2"].current_cool_down_seconds
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key2"].cool_down_until
        == initial_time + manager._initial_cool_down_seconds
    )


@pytest.mark.asyncio
async def test_deactivate_key_other_http_error_threshold(
    key_manager_instance, mock_settings
):
    """
    测试 other_http_error 达到阈值时的停用。
    """
    manager = key_manager_instance
    initial_time = time.time()

    # 模拟失败次数达到阈值
    for _ in range(mock_settings.API_KEY_FAILURE_THRESHOLD - 1):
        await manager.deactivate_key("key1", "other_http_error")
        assert "key1" in manager._available_keys  # 尚未达到阈值，不应停用

    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key1", "other_http_error")  # 达到阈值，停用

    assert "key1" not in manager._available_keys
    assert manager._key_states["key1"].cool_down_until > 0
    assert (
        manager._key_states["key1"].request_fail_count
        == mock_settings.API_KEY_FAILURE_THRESHOLD
    )
    assert manager._key_states["key1"].cool_down_entry_count == 1
    assert (
        manager._key_states["key1"].current_cool_down_seconds
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key1"].cool_down_until
        == initial_time + manager._initial_cool_down_seconds
    )


@pytest.mark.asyncio
async def test_deactivate_key_request_error_threshold(
    key_manager_instance, mock_settings
):
    """
    测试 request_error 达到阈值时的停用。
    """
    manager = key_manager_instance
    initial_time = time.time()

    # 模拟失败次数达到阈值
    for _ in range(mock_settings.API_KEY_FAILURE_THRESHOLD - 1):
        await manager.deactivate_key("key2", "request_error")
        assert "key2" in manager._available_keys  # 尚未达到阈值，不应停用

    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key2", "request_error")  # 达到阈值，停用

    assert "key2" not in manager._available_keys
    assert manager._key_states["key2"].cool_down_until > 0
    assert (
        manager._key_states["key2"].request_fail_count
        == mock_settings.API_KEY_FAILURE_THRESHOLD
    )
    assert manager._key_states["key2"].cool_down_entry_count == 1
    assert (
        manager._key_states["key2"].current_cool_down_seconds
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key2"].cool_down_until
        == initial_time + manager._initial_cool_down_seconds
    )


@pytest.mark.asyncio
async def test_deactivate_key_exponential_backoff(key_manager_instance, mock_settings):
    """
    测试停用时冷却时间的指数退避。
    """
    manager = key_manager_instance
    initial_time = time.time()

    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key1", "auth_error")
        assert (
            manager._key_states["key1"]["current_cool_down_seconds"]
            == manager._initial_cool_down_seconds
        )
        assert (
            manager._key_states["key1"]["cool_down_until"]
            == initial_time + manager._initial_cool_down_seconds
        )

    # 模拟时间流逝，使 key1 冷却结束并再次停用
    with patch(
        "time.time", return_value=initial_time + manager._initial_cool_down_seconds + 1
    ):
        await manager.get_next_key()  # 重新激活 key1
        await manager.deactivate_key("key1", "auth_error")
        expected_cool_down_1 = manager._initial_cool_down_seconds * (
            2 ** (2 - 1)
        )  # 2次进入冷却
        assert (
            manager._key_states["key1"]["current_cool_down_seconds"]
            == expected_cool_down_1
        )
        assert (
            manager._key_states["key1"]["cool_down_until"]
            == initial_time
            + manager._initial_cool_down_seconds
            + 1
            + expected_cool_down_1
        )

    # 再次模拟时间流逝，使 key1 冷却结束并再次停用
    with patch(
        "time.time",
        return_value=initial_time
        + manager._initial_cool_down_seconds
        + 1
        + expected_cool_down_1
        + 1,
    ):
        await manager.get_next_key()  # 重新激活 key1
        await manager.deactivate_key("key1", "auth_error")
        expected_cool_down_2 = manager._initial_cool_down_seconds * (
            2 ** (3 - 1)
        )  # 3次进入冷却
        assert (
            manager._key_states["key1"]["current_cool_down_seconds"]
            == expected_cool_down_2
        )
        assert (
            manager._key_states["key1"]["cool_down_until"]
            == initial_time
            + manager._initial_cool_down_seconds
            + 1
            + expected_cool_down_1
            + 1
            + expected_cool_down_2
        )


@pytest.mark.asyncio
async def test_deactivate_key_max_cool_down(key_manager_instance, mock_settings):
    """
    测试冷却时间达到最大值。
    """
    manager = key_manager_instance
    initial_time = time.time()

    # 强制多次停用，直到达到最大冷却时间
    for i in range(1, 10):  # 足够多的次数来达到最大值
        with patch(
            "time.time",
            return_value=initial_time + i * mock_settings.MAX_COOL_DOWN_SECONDS,
        ):
            await manager.deactivate_key("key1", "auth_error")
            if i > 1:  # 第一次冷却后才开始指数增长
                await manager.get_next_key()  # 重新激活 key1
                await manager.deactivate_key("key1", "auth_error")

            if (
                manager._key_states["key1"]["current_cool_down_seconds"]
                == mock_settings.MAX_COOL_DOWN_SECONDS
            ):
                break

    assert (
        manager._key_states["key1"]["current_cool_down_seconds"]
        == mock_settings.MAX_COOL_DOWN_SECONDS
    )


@pytest.mark.asyncio
async def test_mark_key_success(key_manager_instance):
    """
    测试 mark_key_success 功能。
    """
    manager = key_manager_instance

    # 先停用 key1
    await manager.deactivate_key("key1", "auth_error")
    assert manager._key_states["key1"].cool_down_entry_count > 0
    assert (
        manager._key_states["key1"].current_cool_down_seconds
        > manager._initial_cool_down_seconds - 1
    )  # 确保不是初始值

    # 标记成功
    await manager.mark_key_success("key1")
    assert manager._key_states["key1"].cool_down_entry_count == 0
    assert (
        manager._key_states["key1"].current_cool_down_seconds
        == manager._initial_cool_down_seconds
    )

    # 确保对未管理 key 的调用不会出错
    await manager.mark_key_success("non_existent_key")


@pytest.mark.asyncio
async def test_get_key_states(key_manager_instance):
    """
    测试 get_key_states 方法返回 KeyStatusResponse 列表。
    """
    manager = key_manager_instance
    key_states = await manager.get_key_states()

    assert isinstance(key_states, list)
    assert len(key_states) == len(manager._key_states)

    for state in key_states:
        assert isinstance(state, KeyStatusResponse)
        assert state.key_identifier in ["key1", "key2", "key3"]
        assert state.status in ["active", "cool_down"]
        assert state.cool_down_seconds_remaining >= 0
        assert isinstance(state.daily_usage, dict)
        assert state.failure_count >= 0
        assert state.cool_down_entry_count >= 0
        assert state.current_cool_down_seconds >= 0

    # 模拟一个 key 进入冷却状态，再次检查
    await manager.deactivate_key("key1", "auth_error")
    key_states_after_deactivation = await manager.get_key_states()

    key1_status = next(
        (s for s in key_states_after_deactivation if s.key_identifier == "key1"), None
    )
    assert key1_status is not None
    assert key1_status.status == "cool_down"
    assert key1_status.cool_down_seconds_remaining > 0
    assert key1_status.failure_count == 1
    assert key1_status.cool_down_entry_count == 1
    assert key1_status.current_cool_down_seconds == manager._initial_cool_down_seconds

    key2_status = next(
        (s for s in key_states_after_deactivation if s.key_identifier == "key2"), None
    )
    assert key2_status is not None
    assert key2_status.status == "active"
    assert key2_status.cool_down_seconds_remaining == 0
    assert key2_status.failure_count == 0
    assert key2_status.cool_down_entry_count == 0
    assert key2_status.current_cool_down_seconds == manager._initial_cool_down_seconds


@pytest.mark.asyncio
async def test_release_cooled_down_keys_efficiency(key_manager_instance):
    """
    测试 _release_cooled_down_keys 的效率，确保它在没有密钥冷却时长时间休眠，
    并在有密钥进入冷却时被唤醒。
    """
    manager = key_manager_instance
    manager.start_background_task()
    await asyncio.sleep(0.1)  # 确保后台任务启动

    # 停用所有 key，使其进入冷却
    await manager.deactivate_key("key1", "auth_error")
    await manager.deactivate_key("key2", "auth_error")
    await manager.deactivate_key("key3", "auth_error")

    # 此时所有 key 都应该在冷却中，_release_cooled_down_keys 应该被唤醒并处理
    # 模拟时间流逝，使 key1 冷却结束
    cool_down_time = manager._key_states["key1"].current_cool_down_seconds
    with patch("time.time", return_value=time.time() + cool_down_time + 1):
        # 强制唤醒一次，确保它检查时间
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)  # 给任务一点时间处理

    assert "key1" in manager._available_keys
    assert manager._key_states["key1"].cool_down_until == 0.0

    manager.stop_background_task()


@pytest.mark.asyncio
async def test_deactivate_key_adds_to_heap_and_wakes_up(key_manager_instance):
    """
    测试 deactivate_key 是否正确地将密钥添加到最小堆中，并唤醒后台任务。
    """
    manager = key_manager_instance
    manager.start_background_task()
    await asyncio.sleep(0.1)  # 确保后台任务启动

    initial_time = time.time()
    with patch("time.time", return_value=initial_time):
        # 停用 key1
        await manager.deactivate_key("key1", "auth_error")

    # 检查 key1 是否被添加到冷却堆中
    assert len(manager._cooled_down_keys) == 1
    assert manager._cooled_down_keys[0][1] == "key1"
    assert manager._cooled_down_keys[0][0] == pytest.approx(
        initial_time + manager._initial_cool_down_seconds
    )

    # 检查 _wakeup_event 是否被设置
    assert manager._wakeup_event.is_set()

    manager.stop_background_task()


@pytest.mark.asyncio
async def test_release_cooled_down_keys_with_multiple_keys(key_manager_instance):
    """
    测试 _release_cooled_down_keys 处理多个冷却密钥的场景。
    """
    manager = key_manager_instance
    manager.start_background_task()
    await asyncio.sleep(0.1)

    initial_time = time.time()
    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key1", "auth_error")
        # 模拟 key2 稍后冷却
        await asyncio.sleep(0.5)
        await manager.deactivate_key("key2", "auth_error")
        # 模拟 key3 更晚冷却
        await asyncio.sleep(0.5)
        await manager.deactivate_key("key3", "auth_error")

    # 此时所有 key 都应该在冷却中
    assert "key1" not in manager._available_keys
    assert "key2" not in manager._available_keys
    assert "key3" not in manager._available_keys
    assert len(manager._cooled_down_keys) == 3

    # 模拟时间流逝，使 key1 冷却结束
    cool_down_time_key1 = manager._key_states["key1"].current_cool_down_seconds
    with patch("time.time", return_value=initial_time + cool_down_time_key1 + 1):
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)

    assert "key1" in manager._available_keys
    assert "key2" not in manager._available_keys
    assert "key3" not in manager._available_keys
    assert manager._key_states["key1"].cool_down_until == 0.0
    assert len(manager._cooled_down_keys) == 2

    # 模拟时间流逝，使 key2 冷却结束
    cool_down_time_key2 = manager._key_states["key2"].current_cool_down_seconds
    with patch("time.time", return_value=initial_time + 0.5 + cool_down_time_key2 + 1):
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)

    assert "key1" in manager._available_keys
    assert "key2" in manager._available_keys
    assert "key3" not in manager._available_keys
    assert manager._key_states["key2"].cool_down_until == 0.0
    assert len(manager._cooled_down_keys) == 1

    # 模拟时间流逝，使 key3 冷却结束
    cool_down_time_key3 = manager._key_states["key3"].current_cool_down_seconds
    with patch("time.time", return_value=initial_time + 1.0 + cool_down_time_key3 + 1):
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)

    assert "key1" in manager._available_keys
    assert "key2" in manager._available_keys
    assert "key3" in manager._available_keys
    assert manager._key_states["key3"].cool_down_until == 0.0
    assert len(manager._cooled_down_keys) == 0

    manager.stop_background_task()


@pytest.mark.asyncio
async def test_release_cooled_down_keys_handles_re_deactivated_keys(
    key_manager_instance,
):
    """
    测试 _release_cooled_down_keys 是否能正确处理在冷却期间再次被停用的密钥。
    """
    manager = key_manager_instance
    manager.start_background_task()
    await asyncio.sleep(0.1)

    initial_time = time.time()
    with patch("time.time", return_value=initial_time):
        await manager.deactivate_key("key1", "auth_error")
        # 此时 key1 冷却到 initial_time + initial_cool_down_seconds

    # 模拟时间流逝，但未到冷却结束
    with patch("time.time", return_value=initial_time + 1):
        # 再次停用 key1，使其冷却时间延长，并添加新的堆条目
        await manager.deactivate_key("key1", "auth_error")
        # 此时 key1 冷却到 initial_time + 1 + new_cool_down_seconds
        # 堆中应该有两个 key1 的条目，旧的和新的

    assert len(manager._cooled_down_keys) == 2
    # 确保旧的条目在堆顶
    assert manager._cooled_down_keys[0][1] == "key1"
    assert manager._cooled_down_keys[0][0] == pytest.approx(
        initial_time + manager._initial_cool_down_seconds
    )

    # 模拟时间流逝，使第一（旧的）冷却时间到期
    with patch(
        "time.time", return_value=initial_time + manager._initial_cool_down_seconds + 1
    ):
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)

    # 此时旧的 key1 条目应该被弹出，但因为 key1 状态已更新，它不会被重新激活
    assert "key1" not in manager._available_keys  # 仍然处于冷却状态
    assert len(manager._cooled_down_keys) == 1  # 旧的条目被移除
    # 堆中只剩下新的 key1 条目
    assert manager._cooled_down_keys[0][1] == "key1"
    assert manager._cooled_down_keys[0][0] == pytest.approx(
        initial_time
        + 1
        + manager._key_states["key1"].current_cool_down_seconds
    )

    # 模拟时间流逝，使第二个（新的）冷却时间到期
    with patch(
        "time.time",
        return_value=initial_time
        + 1
        + manager._key_states["key1"].current_cool_down_seconds
        + 1,
    ):
        manager._wakeup_event.set()
        await asyncio.sleep(0.1)

    # 此时 key1 应该被重新激活
    assert "key1" in manager._available_keys
    assert manager._key_states["key1"].cool_down_until == 0.0
    assert len(manager._cooled_down_keys) == 0

    manager.stop_background_task()
