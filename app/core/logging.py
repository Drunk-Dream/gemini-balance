import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
