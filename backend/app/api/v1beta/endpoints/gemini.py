from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from starlette.responses import StreamingResponse

from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.config import Settings, get_settings
from backend.app.services.auth_key_manager.auth_service import AuthService
from backend.app.services.chat_service.chat_service import ChatService
from backend.app.services.request_key_manager.key_state_manager import KeyStateManager

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


@router.get("/models")
async def list_models(
    auth_key_alias: str = Depends(verify_api_key),
    key_manager: KeyStateManager = Depends(KeyStateManager),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Forwards the request to list available models from the upstream API.
    """
    key = await key_manager.get_next_key()
    if not key:
        raise HTTPException(status_code=503, detail="No available service API keys.")

    try:
        url = f"{settings.GEMINI_API_BASE_URL}/v1beta/models"
        params = {"key": key.full}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail=e.response.text
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {e}") from e
    finally:
        await key_manager.release_key_from_use(key)
