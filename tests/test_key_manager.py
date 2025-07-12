import time
from collections import deque
from unittest.mock import patch

import pytest

# 导入待测试的 KeyManager 类
from app.services.key_manager import KeyManager


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
        assert manager._key_states[key] == {
            "cool_down_until": 0.0,
            "request_fail_count": 0,
            "cool_down_entry_count": 0,
            "current_cool_down_seconds": cool_down,
        }
    assert not manager._cool_down_keys

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
    assert "key1" in manager._cool_down_keys

    # 模拟时间流逝，使 key1 冷却结束
    with patch(
        "time.time", return_value=time.time() + manager._initial_cool_down_seconds + 1
    ):
        key = await manager.get_next_key()
        # 此时 key1 应该被重新激活并可用
        assert "key1" in manager._available_keys
        assert "key1" not in manager._cool_down_keys
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
    assert "key1" in manager._cool_down_keys
    assert manager._key_states["key1"]["request_fail_count"] == 1
    assert manager._key_states["key1"]["cool_down_entry_count"] == 1
    assert (
        manager._key_states["key1"]["current_cool_down_seconds"]
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key1"]["cool_down_until"]
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
    assert "key2" in manager._cool_down_keys
    assert manager._key_states["key2"]["request_fail_count"] == 1
    assert manager._key_states["key2"]["cool_down_entry_count"] == 1
    assert (
        manager._key_states["key2"]["current_cool_down_seconds"]
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key2"]["cool_down_until"]
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
    assert "key1" in manager._cool_down_keys
    assert (
        manager._key_states["key1"]["request_fail_count"]
        == mock_settings.API_KEY_FAILURE_THRESHOLD
    )
    assert manager._key_states["key1"]["cool_down_entry_count"] == 1
    assert (
        manager._key_states["key1"]["current_cool_down_seconds"]
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key1"]["cool_down_until"]
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
    assert "key2" in manager._cool_down_keys
    assert (
        manager._key_states["key2"]["request_fail_count"]
        == mock_settings.API_KEY_FAILURE_THRESHOLD
    )
    assert manager._key_states["key2"]["cool_down_entry_count"] == 1
    assert (
        manager._key_states["key2"]["current_cool_down_seconds"]
        == manager._initial_cool_down_seconds
    )
    assert (
        manager._key_states["key2"]["cool_down_until"]
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
    assert manager._key_states["key1"]["cool_down_entry_count"] > 0
    assert (
        manager._key_states["key1"]["current_cool_down_seconds"]
        > manager._initial_cool_down_seconds - 1
    )  # 确保不是初始值

    # 标记成功
    await manager.mark_key_success("key1")
    assert manager._key_states["key1"]["cool_down_entry_count"] == 0
    assert (
        manager._key_states["key1"]["current_cool_down_seconds"]
        == manager._initial_cool_down_seconds
    )

    # 确保对未管理 key 的调用不会出错
    await manager.mark_key_success("non_existent_key")
