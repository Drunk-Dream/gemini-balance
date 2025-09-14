import redis.asyncio as redis

from backend.app.core.config import settings
from backend.app.services.auth_key_manager import get_auth_db_manager
from backend.app.services.key_managers import get_key_manager
from backend.app.services.request_logs import get_request_log_manager

redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)

key_manager = get_key_manager(settings)
auth_key_manager = get_auth_db_manager(settings)
request_logs_manager = get_request_log_manager(settings, redis_client)
