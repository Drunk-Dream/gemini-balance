from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatCompletionRequest
from backend.app.services.auth_key_manager import get_auth_manager
from backend.app.services.auth_key_manager.auth_service import AuthService
from backend.app.services.chat_service.openai_service import OpenAIService

router = APIRouter()
security_scheme = HTTPBearer()


async def verify_bearer_token(
    authorization: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: AuthService = Depends(get_auth_manager),
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
    openai_service: OpenAIService = Depends(OpenAIService),
    auth_key_alias: str = Depends(verify_bearer_token),
) -> Union[Dict[str, Any], StreamingResponse, HTTPException]:
    stream = bool(request.stream)
    await openai_service.create_request_info(request.model, auth_key_alias, stream)
    response = await openai_service.create_chat_completion(request)
    return response
