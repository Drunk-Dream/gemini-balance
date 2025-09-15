from fastapi import Depends

from backend.app.core.config import Settings, get_settings
from backend.app.services.chat_service.gemini_service import GeminiService
from backend.app.services.chat_service.openai_service import OpenAIService
from backend.app.services.key_managers.key_state_manager import KeyStateManager


def get_gemini_service(
    settings: Settings = Depends(get_settings),
    key_manager: KeyStateManager = Depends(KeyStateManager),
):
    return GeminiService(settings, key_manager)


def get_chat_service(
    settings: Settings = Depends(get_settings),
    key_manager: KeyStateManager = Depends(KeyStateManager),
):
    return OpenAIService(settings, key_manager)
