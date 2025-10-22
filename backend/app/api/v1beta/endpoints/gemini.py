from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from starlette.responses import StreamingResponse

from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.services.auth_key_manager.auth_service import AuthService
from backend.app.services.chat_service.chat_service import ChatService

router = APIRouter()


async def verify_api_key(
    x_goog_api_key: Optional[str] = Header(None),
    key: Optional[str] = Query(None),
    auth_service: AuthService = Depends(AuthService),
) -> str:
    """
    FastAPI dependency to verify an authentication key from the x-goog-api-key header or key query parameter.
    Returns the AuthKey alias if valid.
    """
    api_key = x_goog_api_key or key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证密钥缺失。请在请求头中提供 x-goog-api-key 或在 URL 参数中提供 key。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_key = await auth_service.get_key(api_key)
    if not auth_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的认证密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_key.alias


@router.post(
    "/models/{model_id}:generateContent",
    response_model=Dict[str, Any],
)
async def generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    chat_service: ChatService = Depends(),
    auth_key_alias: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    await chat_service.create_request_info(model_id, auth_key_alias, False)
    response = await chat_service.create_chat_completion(request)
    return response if isinstance(response, Dict) else {}


@router.post(
    "/models/{model_id}:streamGenerateContent",
    response_model=None,
)
async def stream_generate_content_endpoint(
    model_id: str,
    request: GeminiRequest,
    chat_service: ChatService = Depends(ChatService),
    auth_key_alias: str = Depends(verify_api_key),
) -> StreamingResponse:
    await chat_service.create_request_info(model_id, auth_key_alias, True)
    response = await chat_service.create_chat_completion(request)
    return (
        response
        if isinstance(response, StreamingResponse)
        else StreamingResponse(iter([]))
    )
