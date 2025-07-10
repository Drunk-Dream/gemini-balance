import logging
import sys
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
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))

# Console handler for general application logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    "%(levelname)s - %(name)s - %(message)s"
))

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


def setup_logging():
    """
    Sets up the main application logging.
    The transaction logger is configured separately and does not need to be called here.
    """
    # The app_logger is already configured above.
    # This function is kept for potential future use or if other setup is needed.
    pass
