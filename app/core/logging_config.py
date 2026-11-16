"""
Logging configuration.

Do handlers:
    - Console: INFO+ level, readable format
    - File: INFO+ level, JSON-ish structured, rotating

Rotation:
    - Max 5 MB per file
    - 5 backups (app.log.1, .2, .3, .4, .5)
    - Total disk use: ~25 MB max

Use:
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("PDF uploaded", extra={"doc_id": "..."})
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from app.core.config import settings


LOGS_DIR = settings.PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "app.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB
BACKUP_COUNT = 5
LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)


_configured = False


def configure_logging() -> None:
    """Global logging setup. Idempotent."""
    global _configured
    if _configured:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Clear existing handlers (uvicorn apne handlers add karta hai)
    root.handlers.clear()

    # ---- Console handler ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(LOG_LEVEL)
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    root.addHandler(console)

    # ---- File handler (rotating) ----
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # ---- Third-party loggers ko quiet karo ----
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Module ke liye logger lo (auto-configure)."""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)