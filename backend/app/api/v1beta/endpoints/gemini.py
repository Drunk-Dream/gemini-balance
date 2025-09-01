from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, status
from starlette.responses import StreamingResponse

from backend.app.api.management.schemas.auth_keys import AuthKey
from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.logging import app_logger as logger
from backend.app.services.auth_service import AuthService
from backend.app.services.gemini_service import GeminiService

router = APIRouter()


async def verify_x_goog_api_key(
    x_goog_api_key: str = Header(...),
    auth_service: AuthService = Depends(AuthService),
) -> AuthKey:
    """
    FastAPI dependency to verify an authentication key from the x-goog-api-key header.
    Returns the AuthKey object if valid.
    """
    if not x_goog_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证密钥缺失。请提供 x-goog-api-key。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_key = await auth_service.get_key(x_goog_api_key)
    if not auth_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的认证密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_key


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
