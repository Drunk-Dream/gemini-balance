from datetime import datetime, timedelta, timezone

from fastapi import Header  # Import Header
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.api.management.schemas.auth_keys import AuthKey
from backend.app.core.config import settings
from backend.app.services.auth_service import AuthService

# 用于密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对密码进行哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta):
    """创建 JWT 访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str):
    """解码 JWT 访问令牌"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效的认证凭据: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户（通过验证 JWT 令牌）"""
    payload = decode_access_token(token)
    if payload:
        return payload
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )


security_scheme = HTTPBearer()


async def verify_bearer_token(
    authorization: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: AuthService = Depends(AuthService),
) -> AuthKey:
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
    return auth_key


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
