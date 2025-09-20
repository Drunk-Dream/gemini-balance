import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from backend.app.core.logging import app_logger, log_broadcaster

router = APIRouter()


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
