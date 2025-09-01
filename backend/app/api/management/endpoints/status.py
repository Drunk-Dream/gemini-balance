import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from backend.app.core.logging import app_logger, log_broadcaster
from backend.app.core.security import get_current_user
from backend.app.services import key_manager

router = APIRouter()

ALLOWED_LOG_FILES = {"backend.app.log", "transactions.log"}


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
