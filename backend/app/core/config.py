from logging import Logger

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API 配置
    GEMINI_API_BASE_URL: str = "https://generativelanguage.googleapis.com"
    OPENAI_API_BASE_URL: str = "https://generativelanguage.googleapis.com"
    REQUEST_TIMEOUT_SECONDS: int = 120

    # 日志配置
    LOG_LEVEL: str = "INFO"
    DEBUG_LOG_ENABLED: bool = False
    DEBUG_LOG_FILE: str = "logs/gemini_debug.log"
    LOG_HISTORY_SIZE: int = 100

    # 密钥管理配置
    API_KEY_COOL_DOWN_SECONDS: int = 300
    API_KEY_FAILURE_THRESHOLD: int = 3
    MAX_COOL_DOWN_SECONDS: int = 3600 * 12
    RATE_LIMIT_DEFAULT_WAIT_SECONDS: int = 90
    MAX_RETRIES: int = 3
    NO_KEY_WAIT_SECONDS: int = 5
    KEY_IN_USE_TIMEOUT_SECONDS: int = 300  # 密钥在用状态的超时时间，默认5分钟
    DEFAULT_CHECK_COOLED_DOWN_SECONDS: int = 300

    # 数据库配置
    DATABASE_TYPE: str = "sqlite"
    SQLITE_DB: str = "data/sqlite.db"
    FORCE_RESET_DATABASE: bool = False

    # 认证与安全配置
    PASSWORD: str = "admin"
    SECRET_KEY: str = "your-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Concurrency settings
    MAX_CONCURRENT_REQUESTS: int = 3
    CONCURRENCY_TIMEOUT_SECONDS: float = 60.0

    @field_validator("DATABASE_TYPE")
    def validate_database_type(cls, v: str) -> str:
        if v != "sqlite":
            raise ValueError("DATABASE_TYPE must be 'sqlite'")
        return v


settings = Settings()


async def print_non_sensitive_settings(logger: Logger):
    non_sensitive_settings = {
        "GEMINI_API_BASE_URL": settings.GEMINI_API_BASE_URL,
        "OPENAI_API_BASE_URL": settings.OPENAI_API_BASE_URL,
        "REQUEST_TIMEOUT_SECONDS": settings.REQUEST_TIMEOUT_SECONDS,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "DEBUG_LOG_ENABLED": settings.DEBUG_LOG_ENABLED,
        "LOG_HISTORY_SIZE": settings.LOG_HISTORY_SIZE,
        "API_KEY_COOL_DOWN_SECONDS": settings.API_KEY_COOL_DOWN_SECONDS,
        "API_KEY_FAILURE_THRESHOLD": settings.API_KEY_FAILURE_THRESHOLD,
        "MAX_COOL_DOWN_SECONDS": settings.MAX_COOL_DOWN_SECONDS,
        "RATE_LIMIT_DEFAULT_WAIT_SECONDS": settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS,
        "MAX_RETRIES": settings.MAX_RETRIES,
        "NO_KEY_WAIT_SECONDS": settings.NO_KEY_WAIT_SECONDS,
        "KEY_IN_USE_TIMEOUT_SECONDS": settings.KEY_IN_USE_TIMEOUT_SECONDS,
        "DEFAULT_CHECK_COOLED_DOWN_SECONDS": settings.DEFAULT_CHECK_COOLED_DOWN_SECONDS,
        "DATABASE_TYPE": settings.DATABASE_TYPE,
        "SQLITE_DB": settings.SQLITE_DB,
        "FORCE_RESET_DATABASE": settings.FORCE_RESET_DATABASE,
        "ALGORITHM": settings.ALGORITHM,
        "ACCESS_TOKEN_EXPIRE_MINUTES": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "MAX_CONCURRENT_REQUESTS": settings.MAX_CONCURRENT_REQUESTS,
        "CONCURRENCY_TIMEOUT_SECONDS": settings.CONCURRENCY_TIMEOUT_SECONDS,
    }
    logger.info("Project settings:")
    for key, value in non_sensitive_settings.items():
        logger.info(f"{key}: {value}")
