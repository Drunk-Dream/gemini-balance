import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_API_BASE_URL: str = os.getenv(
        "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_LOG_ENABLED: bool = os.getenv("DEBUG_LOG_ENABLED", "False").lower() == "true"
    DEBUG_LOG_FILE: str = os.getenv("DEBUG_LOG_FILE", "logs/gemini_debug.log")


settings = Settings()
