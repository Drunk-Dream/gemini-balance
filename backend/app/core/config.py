import os
from typing import Any, List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GOOGLE_API_KEYS: Optional[List[str]] = None
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

    @field_validator("GOOGLE_API_KEYS", mode="before")
    @classmethod
    def _parse_api_keys(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return []


settings = Settings()
