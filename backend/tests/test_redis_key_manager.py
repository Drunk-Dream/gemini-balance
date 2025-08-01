import asyncio
import time
from datetime import datetime
from unittest.mock import patch

import pytest
from app.core.logging import app_logger
from app.services.redis_key_manager import (
    KeyStatusResponse,
    RedisKeyManager,
    RedisKeyState,
)


# Mock settings for testing
@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEYS = ["key1", "key2", "key3"]
        mock_settings.API_KEY_COOL_DOWN_SECONDS = 1
        mock_settings.API_KEY_FAILURE_THRESHOLD = 2
        mock_settings.MAX_COOL_DOWN_SECONDS = 6
        yield mock_settings


@pytest.fixture
def redis_client_mock():
    """Mock Redis client using fakeredis for async operations."""
    from fakeredis import FakeAsyncRedis

    client = FakeAsyncRedis()
    return client


@pytest.fixture
async def key_manager(redis_client_mock, mock_settings):
    manager = RedisKeyManager(
        redis_client=redis_client_mock,
        api_keys=mock_settings.GOOGLE_API_KEYS,
        cool_down_seconds=mock_settings.API_KEY_COOL_DOWN_SECONDS,
        api_key_failure_threshold=mock_settings.API_KEY_FAILURE_THRESHOLD,
        max_cool_down_seconds=mock_settings.MAX_COOL_DOWN_SECONDS,
    )
    await manager.initialize_keys()
    return manager
    manager.stop_background_task()


@pytest.mark.asyncio
async def test_initialize_keys(redis_client_mock, mock_settings):
    manager = RedisKeyManager(
        redis_client=redis_client_mock,
        api_keys=mock_settings.GOOGLE_API_KEYS,
        cool_down_seconds=mock_settings.API_KEY_COOL_DOWN_SECONDS,
        api_key_failure_threshold=mock_settings.API_KEY_FAILURE_THRESHOLD,
        max_cool_down_seconds=mock_settings.MAX_COOL_DOWN_SECONDS,
    )
    await manager.initialize_keys()

    # Check available keys list
    available_keys = await redis_client_mock.lrange(manager.AVAILABLE_KEYS_KEY, 0, -1)
    available_keys = [key.decode("utf-8") for key in available_keys]
    assert sorted(available_keys) == sorted(mock_settings.GOOGLE_API_KEYS)

    # Check key states
    for key in mock_settings.GOOGLE_API_KEYS:
        state_data = await redis_client_mock.hgetall(f"{manager.KEY_STATE_PREFIX}{key}")
        assert state_data is not None
        key_state = RedisKeyState.from_redis_hash(
            {k.decode(): v.decode() for k, v in state_data.items()}
        )
        assert (
            key_state.current_cool_down_seconds
            == mock_settings.API_KEY_COOL_DOWN_SECONDS
        )
        assert key_state.request_fail_count == 0
        assert key_state.cool_down_entry_count == 0
        assert key_state.cool_down_until == 0.0


@pytest.mark.asyncio
async def test_get_next_key(key_manager, mock_settings):
    key_manager = await key_manager
    key = await key_manager.get_next_key()
    assert key in mock_settings.GOOGLE_API_KEYS
    # After getting, key should be moved to the end of the queue
    available_keys = await key_manager._redis.lrange(
        key_manager.AVAILABLE_KEYS_KEY, 0, -1
    )
    assert available_keys[-1].decode() == key


@pytest.mark.asyncio
async def test_deactivate_key_auth_error(key_manager, mock_settings):
    key_manager = await key_manager
    key = mock_settings.GOOGLE_API_KEYS[0]
    await key_manager.deactivate_key(key, "auth_error")

    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state.request_fail_count == 1
        assert key_state.cool_down_entry_count == 1
        assert key_state.cool_down_until > time.time()
        assert (
            key_state.current_cool_down_seconds
            == mock_settings.API_KEY_COOL_DOWN_SECONDS
        )

    # Key should be removed from available keys
    available_keys = await key_manager._redis.lrange(
        key_manager.AVAILABLE_KEYS_KEY, 0, -1
    )
    available_keys = [key.decode("utf-8") for key in available_keys]
    assert key not in available_keys

    # Key should be in cooled down set
    cooled_down_keys = await key_manager._redis.zrange(
        key_manager.COOLED_DOWN_KEYS_KEY, 0, -1
    )
    cooled_down_keys = [key.decode("utf-8") for key in cooled_down_keys]
    assert key in cooled_down_keys


@pytest.mark.asyncio
async def test_deactivate_key_other_http_error_threshold(key_manager, mock_settings):
    key_manager = await key_manager
    key = mock_settings.GOOGLE_API_KEYS[0]
    # Fail once
    await key_manager.deactivate_key(key, "other_http_error")
    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state.request_fail_count == 1
        assert key_state.cool_down_entry_count == 0  # Not cooled down yet

    # Fail again to reach threshold
    await key_manager.deactivate_key(key, "other_http_error")
    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state.request_fail_count == 2
        assert key_state.cool_down_entry_count == 1  # Now cooled down
        assert key_state.cool_down_until > time.time()


@pytest.mark.asyncio
async def test_mark_key_success(key_manager, mock_settings):
    key_manager = await key_manager
    key = mock_settings.GOOGLE_API_KEYS[0]
    await key_manager.deactivate_key(key, "auth_error")  # Put key in cool-down
    await key_manager.mark_key_success(key)

    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state.cool_down_entry_count == 0
        assert (
            key_state.current_cool_down_seconds
            == mock_settings.API_KEY_COOL_DOWN_SECONDS
        )


@pytest.mark.asyncio
async def test_record_usage(key_manager, mock_settings):
    key_manager = await key_manager
    key = mock_settings.GOOGLE_API_KEYS[0]
    model = "gemini-pro"

    await key_manager.record_usage(key, model)
    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state is not None
        assert key_state.usage_today[model] == 1

    await key_manager.record_usage(key, model)
    key_state = await key_manager._get_key_state(key)
    if key_state is not None:
        assert key_state is not None
        assert key_state.usage_today[model] == 2

    # Test daily reset
    with patch("app.services.redis_key_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 2)
        mock_datetime.strftime = datetime.strftime  # Ensure strftime works
        await key_manager.record_usage(key, "gemini-ultra")
        key_state = await key_manager._get_key_state(key)
        if key_state is not None:
            assert key_state is not None
            assert key_state.last_usage_date == "2025-01-02"
            assert key_state.usage_today == {"gemini-ultra": 1}


@pytest.mark.asyncio
async def test_get_key_states(key_manager, mock_settings):
    key_manager = await key_manager
    states = await key_manager.get_key_states()
    assert len(states) == len(
        mock_settings.GOOGLE_API_KEYS
        if mock_settings.GOOGLE_API_KEYS is not None
        else []
    )
    for state in states:
        assert isinstance(state, KeyStatusResponse)
        assert state.status == "active"
        assert state.cool_down_seconds_remaining == 0.0
        assert state.failure_count == 0
        assert state.cool_down_entry_count == 0


@pytest.mark.asyncio
async def test_release_cooled_down_keys_background_task(key_manager, mock_settings):
    key_manager = await key_manager
    # Ensure background task is running
    key_manager.start_background_task()

    key = mock_settings.GOOGLE_API_KEYS[0]
    await key_manager.deactivate_key(key, "auth_error")

    await asyncio.sleep(
        mock_settings.API_KEY_COOL_DOWN_SECONDS + 0.5
    )  # Wait for cool-down to expire

    key_state = await key_manager._get_key_state(key)

    if key_state is not None:
        assert key_state.cool_down_until == 0.0
        assert key_state.request_fail_count == 0
        assert key_state.cool_down_entry_count == 1

    available_keys = await key_manager._redis.lrange(
        key_manager.AVAILABLE_KEYS_KEY, 0, -1
    )
    assert key in available_keys
    key_manager.stop_background_task()


@pytest.mark.asyncio
async def test_get_next_key_when_no_keys_available(key_manager, mock_settings):
    key_manager = await key_manager
    key_manager.start_background_task()
    # Deactivate all keys
    api_keys = (
        mock_settings.GOOGLE_API_KEYS
        if mock_settings.GOOGLE_API_KEYS is not None
        else []
    )
    for key in api_keys:
        await key_manager.deactivate_key(key, "auth_error")

    # Try to get a key, should return None after timeout
    with patch.object(app_logger, "warning") as mock_warning:
        key = await key_manager.get_next_key()
        assert key is None
        mock_warning.assert_called_with("Timeout waiting for an available key.")

    key_manager.stop_background_task()


@pytest.mark.asyncio
async def test_exponential_backoff(key_manager, mock_settings):
    key_manager = await key_manager
    key = mock_settings.GOOGLE_API_KEYS[0]
    initial_cool_down = mock_settings.API_KEY_COOL_DOWN_SECONDS

    # First deactivation
    await key_manager.deactivate_key(key, "auth_error")
    state1 = await key_manager._get_key_state(key)
    if state1 is not None:
        assert state1 is not None
        assert state1.current_cool_down_seconds == initial_cool_down

    # Second deactivation (after it's reactivated, for simplicity in test)
    # In a real scenario, you'd wait for it to reactivate or force reactivate
    state1.cool_down_until = 0.0  # Simulate reactivation for test
    await key_manager._save_key_state(key, state1)
    await key_manager._redis.rpush(
        key_manager.AVAILABLE_KEYS_KEY, key
    )  # Put back to available

    await key_manager.deactivate_key(key, "auth_error")
    state2 = await key_manager._get_key_state(key)
    if state2 is not None:
        assert state2 is not None
        assert state2.current_cool_down_seconds == initial_cool_down * 2

    # Third deactivation
    state2.cool_down_until = 0.0
    await key_manager._save_key_state(key, state2)
    await key_manager._redis.rpush(key_manager.AVAILABLE_KEYS_KEY, key)

    await key_manager.deactivate_key(key, "auth_error")
    state3 = await key_manager._get_key_state(key)
    if state3 is not None:
        assert state3 is not None
        assert state3.current_cool_down_seconds == initial_cool_down * 4

    # Fourth deactivation, should cap at MAX_COOL_DOWN_SECONDS
    state3.cool_down_until = 0.0
    await key_manager._save_key_state(key, state3)
    await key_manager._redis.rpush(key_manager.AVAILABLE_KEYS_KEY, key)

    await key_manager.deactivate_key(key, "auth_error")
    state4 = await key_manager._get_key_state(key)
    if state4 is not None:
        assert state4 is not None
        assert state4.current_cool_down_seconds == mock_settings.MAX_COOL_DOWN_SECONDS
