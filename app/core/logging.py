import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging():
    log_level = settings.LOG_LEVEL.upper()
    numeric_log_level = getattr(logging, log_level, logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(levelname)s - %(name)s - %(message)s"
    ))

    logging.basicConfig(
        level=numeric_log_level,
        handlers=[file_handler, console_handler]
    )

    # Suppress verbose logging from libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
