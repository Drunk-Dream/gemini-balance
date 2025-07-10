import logging
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/models/{model_id}:generateContent",
    response_model=None,
)
async def generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    stream: bool = Query(False),
    gemini_service: GeminiService = Depends(GeminiService),
) -> Union[Dict[str, Any], StreamingResponse]:
    logger.info(f"Received request for model: {model_id}, stream: {stream}")
    response = await gemini_service.generate_content(model_id, request, stream)
    return response
