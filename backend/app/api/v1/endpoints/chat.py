from typing import Any, Dict, Union

from app.api.management.schemas.auth import AuthKey
from app.api.v1.schemas.chat import ChatCompletionRequest
from app.core.logging import app_logger as logger
from app.core.security import verify_bearer_token
from app.services.openai_service import OpenAIService
from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

router = APIRouter()


@router.post(
    "/chat/completions",
    response_model=Union[Dict[str, Any], None],
)
async def create_chat_completion_endpoint(
    request: ChatCompletionRequest,
    openai_service: OpenAIService = Depends(OpenAIService),
    auth_key: AuthKey = Depends(verify_bearer_token),
) -> Union[Dict[str, Any], StreamingResponse]:
    logger.info(
        f"Received OpenAI request from '{auth_key.alias}' for model: {request.model}, stream: {request.stream}"
    )
    response = await openai_service.create_chat_completion(request)
    return response
