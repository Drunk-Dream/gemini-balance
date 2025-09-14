from typing import Union

import redis.asyncio as redis

from backend.app.core.config import Settings
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.redis_manager import RedisRequestLogManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.sqlite_manager import SQLiteRequestLogManager


def get_request_log_manager(
    settings_obj: Settings, redis_client: Union[redis.Redis, None] = None
) -> RequestLogManager:
    """
    根据配置返回正确的 RequestLogManager 实例。
    """
    if settings_obj.DATABASE_TYPE == "sqlite":
        db_manager: RequestLogDBManager = SQLiteRequestLogManager(settings_obj)
    elif settings_obj.DATABASE_TYPE == "redis":
        if not redis_client:
            raise ValueError("Redis client must be provided for Redis database type.")
        db_manager = RedisRequestLogManager(redis_client)
    else:
        raise ValueError(f"Unsupported database type: {settings_obj.DATABASE_TYPE}")
    return RequestLogManager(db_manager=db_manager)
