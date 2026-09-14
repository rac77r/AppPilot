from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_PATH = Path.home() / ".local" / "state" / "AppPilot" / "apppilot.log"
LOGGER_NAME = "apppilot"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    success: bool = True,
    exc_info: bool = False,
    **context: Any,
) -> None:
    payload = {
        "event": event,
        "success": success,
        "context": context,
    }
    logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str), exc_info=exc_info)