from backend.app.core.config import Settings
from backend.app.services.request_logs.db_manager import RequestLogDBManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.sqlite_manager import SQLiteRequestLogManager


def get_request_log_manager(
    settings_obj: Settings
) -> RequestLogManager:
    """
    根据配置返回正确的 RequestLogManager 实例。
    """
    if settings_obj.DATABASE_TYPE == "sqlite":
        db_manager: RequestLogDBManager = SQLiteRequestLogManager(settings_obj)
    else:
        raise ValueError(f"Unsupported database type: {settings_obj.DATABASE_TYPE}")
    return RequestLogManager(db_manager=db_manager)
