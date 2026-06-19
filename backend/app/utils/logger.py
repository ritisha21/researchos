"""
app/utils/logger.py — Fixed: removed add_logger_name (incompatible with PrintLogger)
"""
import logging
import structlog
from app.config import settings


def configure_logging() -> None:
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(format="%(message)s", level=log_level)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer = structlog.dev.ConsoleRenderer(colors=False) if settings.debug else structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
