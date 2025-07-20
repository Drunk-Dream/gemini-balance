import logging
from typing import Any, Dict, Optional

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.core.config import settings
from app.services.gemini_service import GeminiService
from fastapi import APIRouter, Depends, Header, HTTPException
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
    gemini_service: GeminiService = Depends(GeminiService),
    api_key: str = Depends(verify_api_key),  # 添加依赖项
) -> Dict[str, Any]:
    logger.info(f"Received request for model: {model_id}, stream: false")
    response = await gemini_service.generate_content(model_id, request, False)
    return response if isinstance(response, Dict) else {}  # Should always be Dict


@router.post(
    "/models/{model_id}:streamGenerateContent",
    response_model=None,
)
async def stream_generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    gemini_service: GeminiService = Depends(GeminiService),
    api_key: str = Depends(verify_api_key),  # 添加依赖项
) -> StreamingResponse:
    logger.info(f"Received request for model: {model_id}, stream: true")
    response = await gemini_service.generate_content(model_id, request, True)
    return (
        response
        if isinstance(response, StreamingResponse)
        else StreamingResponse(iter([]))
    )  # Should always be StreamingResponse
