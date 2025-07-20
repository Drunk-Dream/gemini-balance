import asyncio
import logging
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Deque, List

from app.core.config import settings

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# --- Main Application Logger ---
app_logger = logging.getLogger("app")
app_logger.setLevel(settings.LOG_LEVEL.upper())

# File handler for general application logs
file_handler = logging.FileHandler(log_dir / "app.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Console handler for general application logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter("%(levelname)s - %(name)s - %(message)s")
)

app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)

# Suppress verbose logging from libraries
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# --- Transaction Logger ---
transaction_logger = logging.getLogger("transaction")
transaction_logger.setLevel(logging.INFO)  # Always log transactions at INFO level

# File handler for transaction logs
transaction_file_handler = logging.FileHandler(log_dir / "transactions.log")
# Minimal formatter for transaction logs to easily parse JSON
transaction_file_handler.setFormatter(logging.Formatter("%(message)s"))

transaction_logger.addHandler(transaction_file_handler)

# Prevent transaction logs from propagating to the root logger
transaction_logger.propagate = False


# --- SSE Log Broadcasting ---
class LogBroadcaster:
    """
    Manages active SSE connections and broadcasts log messages to all clients.
    """

    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []
        self._history: Deque[str] = deque(maxlen=settings.LOG_HISTORY_SIZE)

    async def register(self, queue: asyncio.Queue):
        """Registers a new client queue to receive log messages."""
        # Send history to the new client
        for msg in self._history:
            await queue.put(msg)
        self.subscribers.append(queue)

    def unregister(self, queue: asyncio.Queue):
        """Removes a client queue."""
        self.subscribers.remove(queue)

    async def broadcast(self, message: str):
        """Broadcasts a log message to all registered clients."""
        self._history.append(message)
        for queue in self.subscribers:
            await queue.put(message)


# Singleton instance of the broadcaster
log_broadcaster = LogBroadcaster()


class SSELogHandler(logging.Handler):
    """
    A logging handler that broadcasts log records to SSE clients.
    """

    def __init__(self):
        super().__init__()
        self.formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    def emit(self, record):
        """
        Formats the log record and broadcasts it.
        """
        try:
            msg = self.format(record)
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(log_broadcaster.broadcast(msg), loop)
            except RuntimeError:  # No running loop
                asyncio.run(log_broadcaster.broadcast(msg))
        except Exception:
            self.handleError(record)


# Add the SSE handler to the application logger
app_logger.addHandler(SSELogHandler())


def setup_debug_logger(logger_name: str) -> logging.Logger:
    """
    Sets up a dedicated debug logger with a rotating file handler.
    """
    debug_logger = logging.getLogger(logger_name)
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.propagate = False  # Prevent propagation to root logger

    if settings.DEBUG_LOG_ENABLED:
        log_file_path = Path(settings.DEBUG_LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        debug_logger.addHandler(file_handler)
    return debug_logger


def setup_logging():
    """
    Sets up the main application logging.
    The transaction logger is configured separately and does not need to be called here.
    """
    # The app_logger is already configured above.
    # This function is kept for potential future use or if other setup is needed.
    pass
