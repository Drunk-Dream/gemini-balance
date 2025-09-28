from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.core.config import Settings, get_settings
from backend.app.core.security import SecurityService

router = APIRouter()


@router.post("/login", summary="用户登录并获取访问令牌")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    security_service: SecurityService = Depends(),
    settings: Settings = Depends(get_settings),
):
    """
    通过用户名和密码进行认证，成功后返回 JWT 访问令牌。
    """
    hashed_password = security_service.get_password_hash(settings.PASSWORD)
    # 对于单用户系统，我们只验证密码
    if not security_service.verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="不正确的用户名或密码",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )  # 令牌有效期
    access_token = security_service.create_access_token(
        data={"sub": "single_user"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
