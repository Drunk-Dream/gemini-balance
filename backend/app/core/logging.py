import asyncio
import logging
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Deque, List

from backend.app.core.config import LOG_DIR, settings

# --- Constants ---
APP_LOG_FILE = LOG_DIR / "app.log"
TRANSACTION_LOG_FILE = LOG_DIR / "transactions.log"
DEBUG_LOG_FILE = Path(settings.DEBUG_LOG_FILE)

APP_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
CONSOLE_FORMATTER = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
TRANSACTION_FORMATTER = logging.Formatter("%(message)s")
DEBUG_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Loggers ---
app_logger = logging.getLogger("app")
transaction_logger = logging.getLogger("transaction")


def setup_app_logger() -> None:
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
    app_logger.addHandler(SSELogHandler())

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


def setup_debug_logger(logger_name: str) -> logging.Logger:
    """
    Sets up a dedicated debug logger with a rotating file handler.

    Args:
        logger_name: The name for the debug logger.

    Returns:
        The configured logger instance.
    """
    debug_logger = logging.getLogger(logger_name)
    if debug_logger.handlers:
        debug_logger.handlers.clear()

    debug_logger.setLevel(logging.DEBUG)
    debug_logger.propagate = False

    if settings.DEBUG_LOG_ENABLED:
        DEBUG_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            DEBUG_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(DEBUG_FORMATTER)
        debug_logger.addHandler(file_handler)

    return debug_logger


# --- SSE Log Broadcasting ---
class LogBroadcaster:
    """
    Manages active SSE connections and broadcasts log messages to all clients.
    """

    def __init__(self) -> None:
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


log_broadcaster = LogBroadcaster()


class SSELogHandler(logging.Handler):
    """
    A logging handler that broadcasts log records to SSE clients.
    """

    def __init__(self) -> None:
        """Initializes the handler and its formatter."""
        super().__init__()
        self.formatter = APP_FORMATTER

    def emit(self, record: logging.LogRecord) -> None:
        """
        Formats the log record and broadcasts it asynchronously.
        """
        try:
            msg = self.format(record)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(log_broadcaster.broadcast(msg), loop)
            else:
                # This path is less common in async apps but provides a fallback.
                asyncio.run(log_broadcaster.broadcast(msg))
        except Exception:
            self.handleError(record)
