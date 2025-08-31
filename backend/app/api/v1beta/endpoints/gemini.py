from typing import Any, Dict

from app.api.management.schemas.auth import AuthKey
from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.core.logging import app_logger as logger
from app.core.security import verify_x_goog_api_key
from app.services.gemini_service import GeminiService
from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

router = APIRouter()


@router.post(
    "/models/{model_id}:generateContent",
    response_model=Dict[str, Any],
)
async def generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    gemini_service: GeminiService = Depends(GeminiService),
    auth_key: AuthKey = Depends(verify_x_goog_api_key),
) -> Dict[str, Any]:
    logger.info(
        f"Received Gemini request from '{auth_key.alias}' for model: {model_id}, stream: false"
    )
    response = await gemini_service.generate_content(model_id, request, False)
    return response if isinstance(response, Dict) else {}


@router.post(
    "/models/{model_id}:streamGenerateContent",
    response_model=None,
)
async def stream_generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    gemini_service: GeminiService = Depends(GeminiService),
    auth_key: AuthKey = Depends(verify_x_goog_api_key),
) -> StreamingResponse:
    logger.info(
        f"Received Gemini request from '{auth_key.alias}' for model: {model_id}, stream: true"
    )
    response = await gemini_service.generate_content(model_id, request, True)
    return (
        response
        if isinstance(response, StreamingResponse)
        else StreamingResponse(iter([]))
    )
