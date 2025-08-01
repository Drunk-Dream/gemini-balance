import asyncio
import heapq
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import Settings, settings
from app.core.logging import app_logger
from app.services.key_manager import KeyManager, KeyState, KeyStatusResponse


class SQLiteKeyManager(KeyManager):
    def __init__(
        self,
        settings: Settings,
    ):
        super().__init__(settings)
        self.sqlite_db = Path(settings.SQLITE_DB)
        if not self.sqlite_db.parent.exists():
            self.sqlite_db.parent.mkdir(parents=True, exist_ok=True)
        self._available_keys: List[Tuple[float, str]] = (
            []
        )  # (last_usage_time, key) min-heap
        self._cooled_down_keys: List[Tuple[float, str]] = (
            []
        )  # (cool_down_until, key) min-heap
        self._in_use_keys: set[str] = set()  # 正在使用的 key_identifier 列表
        self._available_keys_set: set[str] = (
            set()
        )  # 可用密钥的 key_identifier 集合，用于快速查找
        self._key_states: Dict[str, KeyState] = {}  # 内存中的 KeyState 缓存

    def _sync_execute_query(self, query: str, params: tuple = ()):
        """同步执行 SQLite 查询。"""
        with sqlite3.connect(self.sqlite_db) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()

    async def _execute_query(self, query: str, params: tuple = ()):
        """在单独的线程中执行 SQLite 查询，避免阻塞事件循环。"""
        return await asyncio.to_thread(self._sync_execute_query, query, params)

    async def initialize(self):
        """初始化数据库，创建表并同步密钥。"""
        await self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_identifier TEXT PRIMARY KEY
            )
            """
        )
        await self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS key_states (
                key_identifier TEXT PRIMARY KEY,
                cool_down_until REAL,
                request_fail_count INTEGER,
                cool_down_entry_count INTEGER,
                current_cool_down_seconds INTEGER,
                usage_today TEXT,
                last_usage_date TEXT,
                last_usage_time REAL
            )
            """
        )
        await self._sync_keys_with_db()
        await self._load_key_states_from_db()

    def _sync_keys_with_db_sync(self):
        """将配置中的密钥与数据库同步（同步版本）。"""
        with sqlite3.connect(self.sqlite_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key_identifier FROM api_keys")
            db_keys = {row[0] for row in cursor.fetchall()}
            config_keys = set(self._api_keys)

            # 添加新密钥
            for key_identifier in config_keys - db_keys:
                cursor.execute(
                    "INSERT INTO api_keys (key_identifier) VALUES (?)", (key_identifier,)
                )
                initial_state = KeyState(
                    current_cool_down_seconds=self._initial_cool_down_seconds
                )
                cursor.execute(
                    """
                    INSERT INTO key_states (
                        key_identifier, cool_down_until, request_fail_count,
                        cool_down_entry_count, current_cool_down_seconds,
                        usage_today, last_usage_date, last_usage_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key_identifier,
                        initial_state.cool_down_until,
                        initial_state.request_fail_count,
                        initial_state.cool_down_entry_count,
                        initial_state.current_cool_down_seconds,
                        json.dumps(initial_state.usage_today),
                        initial_state.last_usage_date,
                        initial_state.last_usage_time,
                    ),
                )
                app_logger.info(f"Added new API key '{key_identifier}' to DB.")

            # 移除不再使用的密钥
            for key_identifier in db_keys - config_keys:
                cursor.execute(
                    "DELETE FROM api_keys WHERE key_identifier = ?", (key_identifier,)
                )
                cursor.execute(
                    "DELETE FROM key_states WHERE key_identifier = ?", (key_identifier,)
                )
                app_logger.info(f"Removed API key '{key_identifier}' from DB.")
            conn.commit()

    async def _sync_keys_with_db(self):
        """将配置中的密钥与数据库同步。"""
        await asyncio.to_thread(self._sync_keys_with_db_sync)

    async def _load_key_states_from_db(self):
        """从数据库加载密钥状态到内存。"""
        self._key_states.clear()
        self._available_keys.clear()
        self._cooled_down_keys.clear()
        self._available_keys_set.clear()

        rows = await self._execute_query("SELECT * FROM key_states")
        now = time.time()

        for row in rows:
            (
                key_identifier,
                cool_down_until,
                request_fail_count,
                cool_down_entry_count,
                current_cool_down_seconds,
                usage_today_json,
                last_usage_date,
                last_usage_time,
            ) = row

            key_state = KeyState(
                cool_down_until=cool_down_until,
                request_fail_count=request_fail_count,
                cool_down_entry_count=cool_down_entry_count,
                current_cool_down_seconds=current_cool_down_seconds,
                usage_today=json.loads(usage_today_json),
                last_usage_date=last_usage_date,
                last_usage_time=last_usage_time,
            )
            self._key_states[key_identifier] = key_state

            if key_state.cool_down_until > now:
                heapq.heappush(
                    self._cooled_down_keys, (key_state.cool_down_until, key_identifier)
                )
            else:
                heapq.heappush(
                    self._available_keys, (key_state.last_usage_time, key_identifier)
                )
                self._available_keys_set.add(key_identifier)
        app_logger.info("API key states loaded from database.")

    async def _release_cooled_down_keys(self):
        while True:
            async with self._lock:
                now = time.time()
                # 释放所有已冷却完毕的密钥
                while self._cooled_down_keys and self._cooled_down_keys[0][0] <= now:
                    cool_down_until, key_identifier = heapq.heappop(
                        self._cooled_down_keys
                    )
                    # 检查密钥是否仍然处于冷却状态且不在可用集合中
                    if (
                        self._key_states[key_identifier].cool_down_until
                        == cool_down_until
                        and key_identifier not in self._available_keys_set
                    ):
                        self._key_states[key_identifier].cool_down_until = 0.0
                        self._key_states[key_identifier].request_fail_count = 0
                        heapq.heappush(
                            self._available_keys, (time.time(), key_identifier)
                        )  # 重新加入可用队列
                        self._available_keys_set.add(key_identifier)  # 添加到可用集合
                        await self._update_key_state_in_db(
                            key_identifier, self._key_states[key_identifier]
                        )
                        app_logger.info(f"API key '{key_identifier}' reactivated.")
                    # 如果密钥状态已改变（例如，在冷却期间再次被停用），则忽略此旧条目
                    # 并继续检查下一个堆顶元素
                self._wakeup_event.clear()  # 清除事件，等待下一次设置

                if self._cooled_down_keys:
                    next_release_time = self._cooled_down_keys[0][0]
                    sleep_duration = max(0.1, next_release_time - time.time())
                else:
                    sleep_duration = (
                        3600  # 如果没有冷却中的密钥，长时间休眠，直到有新密钥进入冷却
                    )

            try:
                # 等待唤醒事件或休眠直到下一个密钥冷却结束
                await asyncio.wait_for(
                    self._wakeup_event.wait(), timeout=sleep_duration
                )
            except asyncio.TimeoutError:
                pass  # 超时是预期行为，表示到达了下一个密钥的冷却时间

    async def start_background_task(self):
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._release_cooled_down_keys()
            )

    def stop_background_task(self):
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def get_next_key(self) -> Optional[str]:
        async with self._lock:
            if not self._available_keys:
                app_logger.warning("No available API keys.")
                return None

            _, key_identifier = heapq.heappop(self._available_keys)
            # 将密钥标识符放入 _in_use_keys 集合
            self._in_use_keys.add(key_identifier)
            self._available_keys_set.discard(key_identifier)  # 从可用集合中移除

            # 更新内存中的 last_usage_time
            self._key_states[key_identifier].last_usage_time = time.time()

            # 更新数据库
            await self._update_key_state_in_db(
                key_identifier, self._key_states[key_identifier]
            )
            return key_identifier

    async def mark_key_fail(self, key_identifier: str, error_type: str):
        async with self._lock:
            if key_identifier not in self._key_states:
                return

            # 从 _in_use_keys 中移除
            if key_identifier in self._in_use_keys:
                self._in_use_keys.discard(key_identifier)

            key_state = self._key_states[key_identifier]
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
                heapq.heappush(
                    self._cooled_down_keys,
                    (key_state.cool_down_until, key_identifier),
                )
                self._wakeup_event.set()  # 唤醒后台任务
                app_logger.warning(
                    f"API key '{key_identifier}' entered cool-down for "
                    f"{key_state.current_cool_down_seconds:.2f} seconds "
                    f"due to {error_type}."
                )
            else:
                # 如果不需要冷却，则放回可用队列和集合
                heapq.heappush(self._available_keys, (time.time(), key_identifier))
                self._available_keys_set.add(key_identifier)
                app_logger.info(
                    f"API key '{key_identifier}' failed but not cooled down, returned to available pool."
                )

            await self._update_key_state_in_db(key_identifier, key_state)

    async def mark_key_success(self, key_identifier: str):
        async with self._lock:
            if key_identifier not in self._key_states:
                return

            # 从 _in_use_keys 中移除
            if key_identifier in self._in_use_keys:
                self._in_use_keys.discard(key_identifier)

            key_state = self._key_states[key_identifier]
            # 成功时重置 cool_down_entry_count 和 current_cool_down_seconds
            key_state.cool_down_entry_count = 0
            key_state.current_cool_down_seconds = self._initial_cool_down_seconds
            key_state.request_fail_count = 0  # 成功时重置失败计数

            # 将密钥放回可用队列和集合
            heapq.heappush(self._available_keys, (time.time(), key_identifier))
            self._available_keys_set.add(key_identifier)
            app_logger.info(
                f"API key '{key_identifier}' marked as success and returned to available pool."
            )

            await self._update_key_state_in_db(key_identifier, key_state)

    async def record_usage(self, key_identifier: str, model: str):
        """记录指定 key 和模型的用量。"""
        async with self._lock:
            if key_identifier not in self._key_states:
                return

            key_state = self._key_states[key_identifier]
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 如果日期变更，重置当日用量
            if key_state.last_usage_date != today_str:
                key_state.usage_today = {}
                key_state.last_usage_date = today_str

            key_state.usage_today[model] = key_state.usage_today.get(model, 0) + 1
            await self._update_key_state_in_db(key_identifier, key_state)
            app_logger.debug(
                f"Key '{key_identifier}' usage for model '{model}': "
                f"{key_state.usage_today[model]}"
            )

    async def get_key_states(self) -> List[KeyStatusResponse]:
        """返回所有 API key 的详细状态列表。"""
        async with self._lock:
            states = []
            now = time.time()
            # 从数据库获取最新状态
            rows = await self._execute_query("SELECT * FROM key_states")
            for row in rows:
                (
                    key_identifier,
                    cool_down_until,
                    request_fail_count,
                    cool_down_entry_count,
                    current_cool_down_seconds,
                    usage_today_json,
                    last_usage_date,
                    last_usage_time,
                ) = row
                key_state = KeyState(
                    cool_down_until=cool_down_until,
                    request_fail_count=request_fail_count,
                    cool_down_entry_count=cool_down_entry_count,
                    current_cool_down_seconds=current_cool_down_seconds,
                    usage_today=json.loads(usage_today_json),
                    last_usage_date=last_usage_date,
                    last_usage_time=last_usage_time,
                )

                cool_down_remaining = max(0, key_state.cool_down_until - now)
                status = "cooling_down" if cool_down_remaining > 0 else "active"

                states.append(
                    KeyStatusResponse(
                        key_identifier=f"{key_identifier}",
                        status=status,
                        cool_down_seconds_remaining=round(cool_down_remaining, 2),
                        daily_usage=key_state.usage_today,
                        failure_count=key_state.request_fail_count,
                        cool_down_entry_count=key_state.cool_down_entry_count,
                        current_cool_down_seconds=key_state.current_cool_down_seconds,
                    )
                )
            return states

    async def _update_key_state_in_db(self, key_identifier: str, key_state: KeyState):
        """更新数据库中指定密钥的状态。"""
        await self._execute_query(
            """
            UPDATE key_states SET
                cool_down_until = ?,
                request_fail_count = ?,
                cool_down_entry_count = ?,
                current_cool_down_seconds = ?,
                usage_today = ?,
                last_usage_date = ?,
                last_usage_time = ?
            WHERE key_identifier = ?
            """,
            (
                key_state.cool_down_until,
                key_state.request_fail_count,
                key_state.cool_down_entry_count,
                key_state.current_cool_down_seconds,
                json.dumps(key_state.usage_today),
                key_state.last_usage_date,
                key_state.last_usage_time,
                key_identifier,
            ),
        )


sqlite_key_manager = SQLiteKeyManager(settings=settings)
