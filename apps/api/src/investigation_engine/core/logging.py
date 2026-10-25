"""Structured logging: JSON in prod, readable console output in dev."""

import logging

import structlog

from investigation_engine.core.config import LogLevel


def configure_logging(level: LogLevel, *, json: bool) -> None:
    logging.basicConfig(format="%(message)s", level=level)
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
    )
