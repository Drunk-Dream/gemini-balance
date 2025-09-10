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

    # 数据库配置
    DATABASE_TYPE: str = "sqlite"
    SQLITE_DB: str = "data/sqlite.db"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    FORCE_RESET_DATABASE: bool = False

    # 认证与安全配置
    PASSWORD: str = "admin"  # Add a default password for simplicity
    SECRET_KEY: str = "your-super-secret-key"  # 从环境变量加载，提供默认值
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Concurrency settings
    MAX_CONCURRENT_REQUESTS: int = 3
    CONCURRENCY_TIMEOUT_SECONDS: float = 60.0

    @field_validator("DATABASE_TYPE")
    def validate_database_type(cls, v: str) -> str:
        if v not in ["redis", "sqlite"]:
            raise ValueError("DATABASE_TYPE must be 'redis' or 'sqlite'")
        return v


settings = Settings()
