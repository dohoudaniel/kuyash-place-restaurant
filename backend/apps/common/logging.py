"""Logging helpers."""

from __future__ import annotations

import contextvars
import logging

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    """Attaches the current request ID to every log record.

    Without this, correlating a payment webhook with the order it settled means
    guessing from timestamps.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
