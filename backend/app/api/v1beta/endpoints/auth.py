from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

# 在应用启动时哈希密码，避免每次请求都哈希
# 生产环境中，密码应通过更安全的方式管理，例如环境变量或密钥管理服务
# 这里为了简化，直接在启动时哈希
hashed_password = get_password_hash(settings.PASSWORD)


@router.post("/login", summary="用户登录并获取访问令牌")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    通过用户名和密码进行认证，成功后返回 JWT 访问令牌。
    """
    # 对于单用户系统，我们只验证密码
    if not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="不正确的用户名或密码",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)  # 令牌有效期
    access_token = create_access_token(
        data={"sub": "single_user"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
