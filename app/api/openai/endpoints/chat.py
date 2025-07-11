import logging
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException
from starlette.responses import StreamingResponse

from app.api.openai.schemas.chat import ChatCompletionRequest
from app.core.config import settings
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_openai_api_key(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Must be 'Bearer YOUR_API_KEY'")
    
    api_key = authorization.split(" ")[1]
    if api_key not in (settings.GOOGLE_API_KEYS or []):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@router.post(
    "/chat/completions",
    response_model=Union[Dict[str, Any], None],
)
async def create_chat_completion_endpoint(
    request: ChatCompletionRequest,
    openai_service: OpenAIService = Depends(OpenAIService),
    api_key: str = Depends(verify_openai_api_key),
) -> Union[Dict[str, Any], StreamingResponse]:
    logger.info(f"Received OpenAI chat completion request for model: {request.model}, stream: {request.stream}")
    response = await openai_service.create_chat_completion(request)
    return response
