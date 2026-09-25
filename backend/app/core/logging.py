import logging
import sys
from typing import Any

import structlog


def configure_logging(env: str = "development") -> None:
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if env == "development":
        processors: list[Any] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
