"""Logging helpers."""

from __future__ import annotations

import contextvars
import logging
from pathlib import Path
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    """Attaches the current request ID to every log record.

    Without this, correlating a payment webhook with the order it settled means
    guessing from timestamps.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


#: Rotate at 5 MB, keep five files: enough to cover a few days of local work
#: without anyone having to remember to delete anything.
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUPS = 5
LOG_FILENAME = "kuyash.log"


def file_handler(
    log_dir: str,
    *,
    formatter: str = "json",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backups: int = DEFAULT_BACKUPS,
) -> dict[str, Any] | None:
    """A rotating file handler for ``log_dir``, or ``None`` when it is blank.

    Deployed environments log to stdout and let the platform collect it: a file
    inside a container disappears on the next deploy, and an unbounded one fills
    the disk. Locally nothing collects stdout — the terminal scrolls away — so a
    file is the only way to answer "what happened in that request ten minutes
    ago". Hence: off unless ``LOG_DIR`` says otherwise, and dev.py says so.

    The file opens on the first record (``delay``), so merely importing settings
    never creates one.
    """
    if not log_dir:
        return None

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        # Log lines carry no emails or phone numbers, but they do record which
        # account signed in and when. Treat the folder as operational data.
        directory.chmod(0o700)
    except OSError:  # pragma: no cover - filesystems that do not support modes
        pass

    return {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(directory / LOG_FILENAME),
        "maxBytes": max_bytes,
        "backupCount": backups,
        "encoding": "utf-8",
        "filters": ["request_id"],
        "formatter": formatter,
        "delay": True,
    }
