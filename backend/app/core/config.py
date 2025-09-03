import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# Define the base directory for logs, ensuring it's relative to the backend root
LOG_DIR = Path("logs")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API 配置
    GEMINI_API_BASE_URL: str = os.getenv(
        "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    OPENAI_API_BASE_URL: str = os.getenv(
        "OPENAI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_LOG_ENABLED: bool = os.getenv("DEBUG_LOG_ENABLED", "False").lower() == "true"
    DEBUG_LOG_FILE: str = os.getenv("DEBUG_LOG_FILE", "logs/gemini_debug.log")
    LOG_HISTORY_SIZE: int = int(os.getenv("LOG_HISTORY_SIZE", "100"))

    # 密钥管理配置
    API_KEY_COOL_DOWN_SECONDS: int = int(os.getenv("API_KEY_COOL_DOWN_SECONDS", "300"))
    API_KEY_FAILURE_THRESHOLD: int = int(os.getenv("API_KEY_FAILURE_THRESHOLD", "3"))
    MAX_COOL_DOWN_SECONDS: int = int(os.getenv("MAX_COOL_DOWN_SECONDS", 3600 * 12))
    RATE_LIMIT_DEFAULT_WAIT_SECONDS: int = int(
        os.getenv("RATE_LIMIT_DEFAULT_WAIT_SECONDS", "90")
    )
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    NO_KEY_WAIT_SECONDS: int = int(os.getenv("NO_KEY_WAIT_SECONDS", "5"))

    # 数据库配置
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")
    SQLITE_DB: str = os.getenv("SQLITE_DB", "data/sqlite.db")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    FORCE_RESET_DATABASE: bool = (
        os.getenv("FORCE_RESET_DATABASE", "False").lower() == "true"
    )

    # 认证与安全配置
    PASSWORD: str = os.getenv(
        "PASSWORD", "admin"
    )  # Add a default password for simplicity
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "your-super-secret-key"
    )  # 从环境变量加载，提供默认值
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Concurrency settings
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))
    CONCURRENCY_TIMEOUT_SECONDS: float = float(
        os.getenv("CONCURRENCY_TIMEOUT_SECONDS", "60.0")
    )

    @field_validator("DATABASE_TYPE")
    def validate_database_type(cls, v: str) -> str:
        if v not in ["redis", "sqlite"]:
            raise ValueError("DATABASE_TYPE must be 'redis' or 'sqlite'")
        return v


settings = Settings()
