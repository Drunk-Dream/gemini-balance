from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class SecurityService:
    """提供密码哈希、JWT 令牌创建和验证等安全相关服务"""

    def __init__(self, settings: Settings = Depends(get_settings)):
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
        self._secret_key = settings.SECRET_KEY
        self._algorithm = settings.ALGORITHM

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证明文密码与哈希密码是否匹配"""
        return self._pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """对密码进行哈希"""
        return self._pwd_context.hash(password)

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta
    ) -> str:
        """创建 JWT 访问令牌"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """解码 JWT 访问令牌"""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的认证凭据: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_user(self, token: str) -> dict[str, Any]:
        """获取当前用户（通过验证 JWT 令牌）"""
        payload = self.decode_access_token(token)
        if payload:
            return payload
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    security: SecurityService = Depends(SecurityService),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/login")),
) -> dict[str, Any]:
    return await security.get_current_user(token)
