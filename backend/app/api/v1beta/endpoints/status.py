import asyncio
from pathlib import Path
from typing import List

from app.core.config import settings
from app.core.logging import app_logger
from app.services.key_manager import key_manager
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()

LOG_DIR = Path("logs")
ALLOWED_LOG_FILES = {"app.log", "transactions.log"}


@router.get("/status/keys", summary="获取所有 API Key 的状态和用量信息")
async def get_api_key_status():
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


@router.websocket("/status/logs/ws")
async def websocket_log_stream(
    websocket: WebSocket,
    log_file_name: str = Query("app.log", description="要监控的日志文件名"),
):
    """
    建立 WebSocket 连接，实时将指定日志文件的新增内容推送到前端。
    """
    if log_file_name not in ALLOWED_LOG_FILES:
        app_logger.warning(
            f"WebSocket: Attempted to access disallowed log file: {log_file_name}"
        )
        await websocket.close(
            code=1008, reason="Access to this log file is not allowed."
        )
        return

    log_file_path = LOG_DIR / log_file_name
    if not log_file_path.exists():
        app_logger.warning(f"WebSocket: Log file not found: {log_file_path}")
        await websocket.close(
            code=1008, reason=f"Log file '{log_file_name}' not found."
        )
        return

    await websocket.accept()
    app_logger.info(f"WebSocket connection established for log file: {log_file_name}")

    try:
        # Open the file and seek to the end
        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # Go to the end of the file

            while True:
                line = f.readline()
                if not line:
                    # No new line, wait a bit and try again
                    await asyncio.sleep(settings.WEBSOCKET_LOG_REFRESH_SECONDS)
                    continue
                await websocket.send_text(line.strip())
    except WebSocketDisconnect:
        app_logger.info(f"WebSocket connection for {log_file_name} disconnected.")
    except Exception as e:
        app_logger.error(f"WebSocket error for {log_file_name}: {e}")
        await websocket.close(code=1011, reason=f"Server error: {e}")
