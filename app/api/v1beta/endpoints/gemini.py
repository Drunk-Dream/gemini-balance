import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/models/{model_id}:generateContent",
    response_model=Dict[str, Any],
)
async def generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    gemini_service: GeminiService = Depends(GeminiService),
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
) -> StreamingResponse:
    logger.info(f"Received request for model: {model_id}, stream: true")
    response = await gemini_service.generate_content(model_id, request, True)
    return (
        response
        if isinstance(response, StreamingResponse)
        else StreamingResponse(iter([]))
    )  # Should always be StreamingResponse
