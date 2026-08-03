"""structlog setup — configured once at startup, used via `get_logger`."""

from __future__ import annotations

import logging

import structlog

from app.config import settings

get_logger = structlog.get_logger


def configure_logging() -> None:
    level = logging.getLevelNamesMapping()[settings.log_level.upper()]
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
