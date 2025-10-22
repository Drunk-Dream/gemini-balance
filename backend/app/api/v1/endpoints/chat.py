from typing import Any, Dict, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatCompletionRequest
from backend.app.core.config import Settings, get_settings
from backend.app.services.auth_key_manager.auth_service import AuthService
from backend.app.services.chat_service.chat_service import ChatService
from backend.app.services.request_key_manager.key_state_manager import KeyStateManager

router = APIRouter()
security_scheme = HTTPBearer()


async def verify_bearer_token(
    authorization: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: AuthService = Depends(AuthService),
) -> str:
    """
    FastAPI dependency to verify an authentication key from the Authorization header (Bearer token).
    Returns the AuthKey object if valid.
    """
    if not authorization or not authorization.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证密钥缺失。请提供 Authorization: Bearer <key>。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = authorization.credentials
    auth_key = await auth_service.get_key(api_key)
    if not auth_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的认证密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_key.alias


@router.post(
    "/chat/completions",
    response_model=Union[Dict[str, Any], None],
)
async def create_chat_completion_endpoint(
    request: ChatCompletionRequest,
    chat_service: ChatService = Depends(),
    auth_key_alias: str = Depends(verify_bearer_token),
) -> Union[Dict[str, Any], StreamingResponse, HTTPException]:
    stream = bool(request.stream)
    await chat_service.create_request_info(request.model, auth_key_alias, stream)
    response = await chat_service.create_chat_completion(request)
    return response


@router.get("/models")
async def list_models(
    authorization: HTTPAuthorizationCredentials = Depends(security_scheme),
    key_manager: KeyStateManager = Depends(KeyStateManager),
    settings: Settings = Depends(get_settings),
):
    """
    Forwards the request to list available models from the upstream API.
    """
    key = await key_manager.get_next_key()
    if not key:
        raise HTTPException(status_code=503, detail="No available service API keys.")

    try:
        url = f"{settings.OPENAI_API_BASE_URL}/models"
        headers = {
            "Authorization": f"Bearer {key.full}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
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
