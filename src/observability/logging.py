"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

from loguru import logger


class InterceptHandler(logging.Handler):
    """Route standard-library logging through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(log_level: str = "INFO", json_logs: bool = False, debug: bool = False) -> None:
    """Configure backend logs as structured Loguru events."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        serialize=json_logs,
        backtrace=debug,
        diagnose=debug,
        format=(
            "{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | "
            "{extra[event]} | {message} | {extra}"
        ),
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=log_level.upper(), force=True)
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy"):
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
        logging.getLogger(logger_name).propagate = False

    logger.configure(extra={"event": "backend_log", "request_id": None})


def event_logger(event: str, **context: Any):
    """Return a Loguru logger bound to a stable event name and context."""
    return logger.bind(event=event, **context)
