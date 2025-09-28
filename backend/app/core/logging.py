import asyncio
import logging
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Deque, List

from fastapi import Request

from backend.app.core.config import Settings

# --- Constants ---
LOG_DIR = Path("logs")
APP_LOG_FILE = LOG_DIR / "app.log"
TRANSACTION_LOG_FILE = LOG_DIR / "transactions.log"

APP_FORMATTER = logging.Formatter("%(asctime)sZ - %(levelname)s - %(message)s")
APP_FORMATTER.converter = time.gmtime
CONSOLE_FORMATTER = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
CONSOLE_FORMATTER.converter = time.gmtime
TRANSACTION_FORMATTER = logging.Formatter("%(asctime)sZ - %(message)s")
TRANSACTION_FORMATTER.converter = time.gmtime

app_logger = logging.getLogger("app")
transaction_logger = logging.getLogger("transaction")


def get_log_broadcaster(request: Request) -> "LogBroadcaster":
    return request.app.state.log_broadcaster


def initialize_logging(settings: Settings) -> "LogBroadcaster":
    log_broadcaster = LogBroadcaster(settings)
    sse_log_handler = SSELogHandler(log_broadcaster)

    setup_app_logger(settings, sse_log_handler)
    setup_transaction_logger()
    return log_broadcaster


# --- SSE Log Broadcasting ---
class LogBroadcaster:
    """
    Manages active SSE connections and broadcasts log messages to all clients.
    """

    def __init__(self, settings: Settings) -> None:
        """Initializes the broadcaster with a list of subscribers and history."""
        self.subscribers: List[asyncio.Queue[str]] = []
        self._history: Deque[str] = deque(maxlen=settings.LOG_HISTORY_SIZE)

    async def register(self, queue: asyncio.Queue[str]) -> None:
        """
        Registers a new client queue and sends them the log history.
        """
        for msg in self._history:
            await queue.put(msg)
        self.subscribers.append(queue)

    def unregister(self, queue: asyncio.Queue[str]) -> None:
        """Removes a client queue."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def broadcast(self, message: str) -> None:
        """
        Broadcasts a log message to all registered clients and saves it to history.
        """
        self._history.append(message)
        for queue in self.subscribers:
            await queue.put(message)


class SSELogHandler(logging.Handler):
    """
    A logging handler that broadcasts log records to SSE clients.
    """

    def __init__(self, log_broadcaster: LogBroadcaster) -> None:
        """Initializes the handler and its formatter."""
        super().__init__()
        self.formatter = APP_FORMATTER
        self._log_broadcaster = log_broadcaster

    def emit(self, record: logging.LogRecord) -> None:
        """
        Formats the log record and broadcasts it asynchronously.
        """
        try:
            msg = self.format(record)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._log_broadcaster.broadcast(msg), loop
                )
            else:
                # This path is less common in async apps but provides a fallback.
                asyncio.run(self._log_broadcaster.broadcast(msg))
        except Exception:
            self.handleError(record)


def setup_app_logger(settings: Settings, sse_log_handler: SSELogHandler) -> None:
    """
    Configures the main application logger.
    - Clears existing handlers to prevent duplicates during hot-reloads.
    - Sets log level from settings.
    - Adds file and console handlers.
    - Adds SSE handler for real-time log streaming.
    - Suppresses verbose logs from third-party libraries.
    """
    if app_logger.handlers:
        app_logger.handlers.clear()

    app_logger.setLevel(settings.LOG_LEVEL.upper())
    app_logger.propagate = False

    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = RotatingFileHandler(
        APP_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(APP_FORMATTER)
    app_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    app_logger.addHandler(console_handler)

    # SSE handler
    app_logger.addHandler(sse_log_handler)

    # Suppress verbose logging from libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def setup_transaction_logger() -> None:
    """
    Configures the transaction logger.
    - Clears existing handlers.
    - Sets log level to INFO.
    - Adds a dedicated file handler.
    - Prevents propagation to the root logger.
    """
    if transaction_logger.handlers:
        transaction_logger.handlers.clear()

    transaction_logger.setLevel(logging.INFO)
    transaction_logger.propagate = False

    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # File handler
    transaction_file_handler = RotatingFileHandler(
        TRANSACTION_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    transaction_file_handler.setFormatter(TRANSACTION_FORMATTER)
    transaction_logger.addHandler(transaction_file_handler)
