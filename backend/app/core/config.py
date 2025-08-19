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

    GEMINI_API_BASE_URL: str = os.getenv(
        "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    OPENAI_API_BASE_URL: str = os.getenv(
        "OPENAI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_LOG_ENABLED: bool = os.getenv("DEBUG_LOG_ENABLED", "False").lower() == "true"
    DEBUG_LOG_FILE: str = os.getenv("DEBUG_LOG_FILE", "logs/gemini_debug.log")
    API_KEY_COOL_DOWN_SECONDS: int = int(os.getenv("API_KEY_COOL_DOWN_SECONDS", "300"))
    API_KEY_FAILURE_THRESHOLD: int = int(os.getenv("API_KEY_FAILURE_THRESHOLD", "3"))
    MAX_COOL_DOWN_SECONDS: int = int(os.getenv("MAX_COOL_DOWN_SECONDS", 3600 * 12))
    RATE_LIMIT_DEFAULT_WAIT_SECONDS: int = int(
        os.getenv("RATE_LIMIT_DEFAULT_WAIT_SECONDS", "90")
    )
    LOG_HISTORY_SIZE: int = int(os.getenv("LOG_HISTORY_SIZE", "100"))
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    FORCE_RESET_DATABASE: bool = (
        os.getenv("FORCE_RESET_DATABASE", "False").lower() == "true"
    )
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    SQLITE_DB: str = os.getenv("SQLITE_DB", "data/sqlite.db")
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")
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

    @field_validator("DATABASE_TYPE")
    def validate_database_type(cls, v: str) -> str:
        if v not in ["redis", "sqlite"]:
            raise ValueError("DATABASE_TYPE must be 'redis' or 'sqlite'")
        return v


settings = Settings()
