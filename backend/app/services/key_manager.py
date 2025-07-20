import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import app_logger
from pydantic import BaseModel, Field


class KeyState(BaseModel):
    cool_down_until: float = 0.0
    request_fail_count: int = 0
    cool_down_entry_count: int = 0
    current_cool_down_seconds: int
    usage_today: Dict[str, int] = Field(default_factory=dict)
    last_usage_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )


class KeyManager:
    def __init__(
        self,
        api_keys: List[str],
        cool_down_seconds: int,
        api_key_failure_threshold: int,
        max_cool_down_seconds: int,
        redis_client: redis.Redis,
    ):
        if not api_keys:
            raise ValueError("API key list cannot be empty.")
        self._api_keys = api_keys  # 存储所有API key
        self._redis = redis_client
        self._initial_cool_down_seconds = cool_down_seconds
        self._api_key_failure_threshold = api_key_failure_threshold
        self._max_cool_down_seconds = max_cool_down_seconds
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._background_task: Optional[asyncio.Task] = None
        self._key_prefix = "gemini_key_state:"
        self._available_keys_zset = (
            "gemini_available_keys"  # Redis Sorted Set for available keys
        )

    async def _load_key_state(self, key: str) -> KeyState:
        state_data = await self._redis.get(f"{self._key_prefix}{key}")
        if state_data:
            try:
                return KeyState.model_validate_json(state_data)
            except Exception as e:
                app_logger.error(f"Failed to load key state for {key}: {e}")
        # If not found or failed to load, return a default state
        return KeyState(current_cool_down_seconds=self._initial_cool_down_seconds)

    async def _save_key_state(self, key: str, state: KeyState):
        await self._redis.set(f"{self._key_prefix}{key}", state.model_dump_json())

    async def initialize_key_states(self):
        """初始化或从Redis加载所有API key的状态"""
        async with self._lock:
            for key in self._api_keys:
                key_state = await self._load_key_state(key)
                # 检查日期，如果不是今天，重置用量
                today_str = datetime.now().strftime("%Y-%m-%d")
                if key_state.last_usage_date != today_str:
                    key_state.usage_today = {}
                    key_state.last_usage_date = today_str
                    await self._save_key_state(key, key_state)

                # 将所有非冷却中的key添加到可用key的Sorted Set中
                if key_state.cool_down_until <= time.time():
                    await self._redis.zadd(
                        self._available_keys_zset, {key: 0}
                    )  # score 0 for active keys
                else:
                    # 如果key仍在冷却中，确保其在Sorted Set中，并设置正确的冷却时间作为score
                    await self._redis.zadd(
                        self._available_keys_zset, {key: key_state.cool_down_until}
                    )
            app_logger.info("API key states initialized/loaded from Redis.")

    async def _release_cooled_down_keys(self):
        """后台任务：定期检查并重新激活冷却结束的key"""
        while True:
            async with self._lock:
                now = time.time()
                # 从Sorted Set中获取所有冷却时间已到的key
                keys_to_reactivate = await self._redis.zrangebyscore(
                    self._available_keys_zset, 0, now
                )

                if keys_to_reactivate:
                    for key_bytes in keys_to_reactivate:
                        key = key_bytes.decode("utf-8")
                        key_state = await self._load_key_state(key)
                        key_state.cool_down_until = 0.0
                        key_state.request_fail_count = 0
                        await self._save_key_state(key, key_state)
                        # 确保score为0，表示活跃
                        await self._redis.zadd(self._available_keys_zset, {key: 0})
                        app_logger.info(f"API key '...{key[-4:]}' reactivated.")
                    self._condition.notify_all()
            # 优化：根据下一个冷却结束时间来决定睡眠多久
            next_cool_down_end = await self._redis.zrange(
                self._available_keys_zset, 0, 0, withscores=True
            )
            if next_cool_down_end and next_cool_down_end[0][1] > now:
                sleep_time = next_cool_down_end[0][1] - now
                await asyncio.sleep(min(sleep_time, 60))  # 最多睡60秒，避免过长
            else:
                # 如果没有即将冷却结束的key，则等待更长时间
                await asyncio.sleep(settings.API_KEY_COOL_DOWN_SECONDS)

    def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def get_next_key(self) -> Optional[str]:
        """从可用key池中获取下一个key"""
        async with self._lock:
            while True:
                # 从Sorted Set中获取一个活跃的key (score为0)
                available_keys = await self._redis.zrangebyscore(
                    self._available_keys_zset, 0, 0, start=0, num=1
                )
                if available_keys:
                    key = available_keys[0].decode("utf-8")
                    # 将key的score更新为当前时间，实现轮询效果
                    await self._redis.zadd(
                        self._available_keys_zset, {key: time.time()}
                    )
                    return key
                else:
                    app_logger.info("No active keys, waiting for keys to cool down...")
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        app_logger.warning("Timeout waiting for an available key.")
                        return None

    async def deactivate_key(self, key: str, error_type: str):
        """将key标记为失效并进入冷却"""
        async with self._lock:
            key_state = await self._load_key_state(key)
            key_state.request_fail_count += 1

            should_cool_down = False
            if error_type in ["auth_error", "rate_limit_error"]:
                should_cool_down = True
            elif error_type in ["other_http_error", "request_error"]:
                if key_state.request_fail_count >= self._api_key_failure_threshold:
                    should_cool_down = True

            if should_cool_down:
                key_state.cool_down_entry_count += 1
                key_state.current_cool_down_seconds = min(
                    self._initial_cool_down_seconds
                    * (2 ** (key_state.cool_down_entry_count - 1)),
                    self._max_cool_down_seconds,
                )
                key_state.cool_down_until = (
                    time.time() + key_state.current_cool_down_seconds
                )
                await self._save_key_state(key, key_state)
                # 将key从可用key池中移除，并更新其在Sorted Set中的score为冷却结束时间
                await self._redis.zadd(
                    self._available_keys_zset, {key: key_state.cool_down_until}
                )
                app_logger.warning(
                    f"API key '...{key[-4:]}' entered cool-down for "
                    f"{key_state.current_cool_down_seconds:.2f} seconds "
                    f"due to {error_type}."
                )
            else:
                await self._save_key_state(key, key_state)  # 保存失败计数

    async def mark_key_success(self, key: str):
        """标记key成功使用，重置失败计数和冷却相关状态"""
        async with self._lock:
            key_state = await self._load_key_state(key)
            key_state.cool_down_entry_count = 0
            key_state.request_fail_count = 0  # 成功时也重置失败计数
            key_state.current_cool_down_seconds = self._initial_cool_down_seconds
            await self._save_key_state(key, key_state)
            # 确保key在可用key池中且score为0
            await self._redis.zadd(self._available_keys_zset, {key: 0})

    async def record_usage(self, key: str, model: str):
        """记录指定 key 和模型的用量。"""
        async with self._lock:
            key_state = await self._load_key_state(key)
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 如果日期变更，重置当日用量
            if key_state.last_usage_date != today_str:
                key_state.usage_today = {}
                key_state.last_usage_date = today_str

            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            await self._save_key_state(key, key_state)
            app_logger.debug(
                f"Key '...{key[-4:]}' usage for model '{model}': "
                f"{key_state.usage_today[model]}"
            )

    async def get_key_states(self) -> List[Dict]:
        """返回所有 API key 的详细状态列表。"""
        async with self._lock:
            states = []
            now = time.time()
            for key in self._api_keys:
                key_state = await self._load_key_state(key)
                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    {
                        "key_identifier": f"...{key[-4:]}",  # 安全起见，只显示后四位
                        "status": status,
                        "cool_down_seconds_remaining": round(cool_down_remaining, 2),
                        "daily_usage": key_state.usage_today,
                        "failure_count": key_state.request_fail_count,
                        "cool_down_entry_count": key_state.cool_down_entry_count,
                        "current_cool_down_seconds": key_state.current_cool_down_seconds,  # noqa:E501
                    }
                )
            return states
