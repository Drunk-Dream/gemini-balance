import asyncio
from datetime import timedelta
from typing import AsyncGenerator, List

from app.core.config import LOG_DIR, settings
from app.core.logging import app_logger, log_broadcaster
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.services import key_manager
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import StreamingResponse

router = APIRouter()

ALLOWED_LOG_FILES = {"app.log", "transactions.log"}

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


@router.get("/status/keys", summary="获取所有 API Key 的状态和用量信息")
async def get_api_key_status(
    current_user: bool = Depends(get_current_user),
):  # 保护此端点
    """
    返回所有配置的 API Key 的详细状态列表，包括：
    - key_identifier: API Key 的部分标识（末尾四位），用于安全展示。
    - status: Key 的当前状态（"active" 或 "cooling_down"）。
    - cool_down_seconds_remaining: 如果 Key 处于冷却状态，剩余的冷却秒数。
    - daily_usage: 一个字典，显示该 Key 下每个模型在当日的用量。
    - failure_count: 该 Key 连续失败的次数。
    - cool_down_entry_count: 该 Key 进入冷却状态的总次数。
    - current_cool_down_seconds: 当前 Key 的冷却时长。
    """
    key_states = await key_manager.get_key_states()
    return {"keys": key_states}


@router.get("/status/logs", summary="获取指定日志文件的最新 N 条日志")
async def get_logs(
    log_file_name: str = Query(
        "app.log", description="要查看的日志文件名 (例如: app.log, transactions.log)"
    ),
    lines: int = Query(100, ge=1, le=1000, description="要获取的日志行数"),
) -> List[str]:
    """
    返回指定日志文件的最新 N 条日志内容。
    """
    if log_file_name not in ALLOWED_LOG_FILES:
        app_logger.warning(f"Attempted to access disallowed log file: {log_file_name}")
        return ["Error: Access to this log file is not allowed."]

    log_file_path = LOG_DIR / log_file_name
    if not log_file_path.exists():
        app_logger.warning(f"Log file not found: {log_file_path}")
        return [f"Error: Log file '{log_file_name}' not found."]

    try:
        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            # Read all lines and take the last 'lines'
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except Exception as e:
        app_logger.error(f"Error reading log file {log_file_name}: {e}")
        return [f"Error reading log file: {e}"]


@router.get("/status/logs/sse", summary="通过 SSE 实时推送应用日志")
async def sse_log_stream() -> StreamingResponse:
    """
    建立 Server-Sent Events (SSE) 连接，实时将应用日志推送到前端。
    """
    client_queue: asyncio.Queue[str] = asyncio.Queue()

    await log_broadcaster.register(client_queue)
    app_logger.debug("SSE client registered for log stream.")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                message = await client_queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            app_logger.debug("SSE client disconnected from log stream.")
        finally:
            log_broadcaster.unregister(client_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
