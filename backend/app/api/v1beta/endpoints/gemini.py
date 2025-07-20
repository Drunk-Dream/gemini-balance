import logging
from typing import Any, Dict, Optional

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.core.config import settings
from app.dependencies import KeyManagerDep
from app.services.gemini_service import GeminiService
from app.services.key_manager import KeyManager
from fastapi import APIRouter, Depends, Header, HTTPException, status
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_api_key(x_goog_api_key: Optional[str] = Header(None)):
    if not x_goog_api_key:
        raise HTTPException(status_code=401, detail="x-goog-api-key header is required")
    if x_goog_api_key not in (settings.GOOGLE_API_KEYS or []):
        raise HTTPException(status_code=401, detail="Invalid x-goog-api-key")
    return x_goog_api_key


@router.post(
    "/models/{model_id}:generateContent",
    response_model=Dict[str, Any],
)
async def generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    key_manager: KeyManagerDep,
    api_key: str = Depends(verify_api_key),  # 添加依赖项
) -> Dict[str, Any]:
    # Type assertion to help Pylance
    km: KeyManager = key_manager
    if not km.has_available_keys():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No available API keys. Please try again later.",
        )
    logger.info(f"Received request for model: {model_id}, stream: false")
    gemini_service = GeminiService(key_manager)
    response = await gemini_service.generate_content(model_id, request, False)
    return response if isinstance(response, Dict) else {}  # Should always be Dict


@router.post(
    "/models/{model_id}:streamGenerateContent",
    response_model=None,
)
async def stream_generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    key_manager: KeyManagerDep,
    api_key: str = Depends(verify_api_key),  # 添加依赖项
) -> StreamingResponse:
    # Type assertion to help Pylance
    km: KeyManager = key_manager
    if not km.has_available_keys():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No available API keys. Please try again later.",
        )
    logger.info(f"Received request for model: {model_id}, stream: true")
    gemini_service = GeminiService(key_manager)
    response = await gemini_service.generate_content(model_id, request, True)
    return (
        response
        if isinstance(response, StreamingResponse)
        else StreamingResponse(iter([]))
    )  # Should always be StreamingResponse
