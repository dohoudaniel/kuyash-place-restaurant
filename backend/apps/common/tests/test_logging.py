"""Logs on disk: off by default, on in local development (SETUP.md §2)."""

from __future__ import annotations

import json
import logging
import logging.config
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from apps.common.logging import DEFAULT_BACKUPS, DEFAULT_MAX_BYTES, file_handler, request_id_var

BACKEND = Path(__file__).resolve().parents[3]

PROBE = """
import json, django
django.setup()
from django.conf import settings as s
print(json.dumps({
    "handlers": sorted(s.LOGGING["handlers"]),
    "root": s.LOGGING["root"]["handlers"],
    "log_dir": s.LOG_DIR,
    "filename": s.LOGGING["handlers"].get("file", {}).get("filename", ""),
}))
"""


def settings_probe(module: str, **overrides: str) -> dict:  # type: ignore[type-arg]
    """Load a settings module in a fresh interpreter; settings are read once per process."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("DJANGO_")}
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": module,
            "DJANGO_SECRET_KEY": "probe-key-not-a-secret-0123456789-abcdefghij-0123456789",
            "ALLOWED_HOSTS": "localhost",
            "DATABASE_URL": "sqlite:///:memory:",
            **overrides,
        }
    )
    result = subprocess.run(  # noqa: S603 - fixed argv, this interpreter
        [sys.executable, "-c", PROBE],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return dict(json.loads(result.stdout.strip().splitlines()[-1]))


# ── The builder ───────────────────────────────────────────────────────────────


def test_no_directory_means_no_file_handler() -> None:
    assert file_handler("") is None


def test_the_builder_creates_the_folder_and_rotates(tmp_path: Path) -> None:
    handler = file_handler(str(tmp_path / "logs"))
    assert handler is not None
    assert (tmp_path / "logs").is_dir()
    assert handler["filename"] == str(tmp_path / "logs" / "kuyash.log")
    assert handler["maxBytes"] == DEFAULT_MAX_BYTES
    assert handler["backupCount"] == DEFAULT_BACKUPS
    assert handler["filters"] == ["request_id"]


def test_the_folder_is_not_world_readable(tmp_path: Path) -> None:
    """Logs record which account signed in and when."""
    file_handler(str(tmp_path / "logs"))
    assert (tmp_path / "logs").stat().st_mode & 0o077 == 0


def test_the_file_is_not_created_until_something_is_logged(tmp_path: Path) -> None:
    file_handler(str(tmp_path / "logs"))
    assert not (tmp_path / "logs" / "kuyash.log").exists()


# ── Records reaching the file ─────────────────────────────────────────────────


@pytest.fixture
def configured(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Install just the file handler, then put logging back as it was."""
    handler = file_handler(str(tmp_path / "logs"))
    assert handler is not None
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": "apps.common.logging.RequestIDFilter"}},
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.json.JsonFormatter",
                    "format": "%(levelname)s %(asctime)s %(name)s %(request_id)s %(message)s",
                }
            },
            "handlers": {"file": handler},
            "loggers": {"apps.probe": {"handlers": ["file"], "level": "INFO", "propagate": False}},
        }
    )
    yield tmp_path / "logs" / "kuyash.log"
    logging.config.dictConfig(settings.LOGGING)


def test_a_record_lands_in_the_file_as_json(configured: Path) -> None:
    token = request_id_var.set("abc123")
    try:
        logging.getLogger("apps.probe").info("order_placed", extra={"order": "KYS-TEST-0001"})
    finally:
        request_id_var.reset(token)
    logging.getLogger("apps.probe").handlers[0].flush()

    line = json.loads(configured.read_text().strip().splitlines()[-1])
    assert line["message"] == "order_placed"
    assert line["request_id"] == "abc123", "a log file is only useful if a request can be traced"
    assert line["order"] == "KYS-TEST-0001"
    assert line["levelname"] == "INFO"


# ── Which environments write files ────────────────────────────────────────────


def test_the_test_suite_writes_no_files() -> None:
    """The suite logs nowhere: test settings keep no handlers, and LOG_DIR is unset."""
    assert settings.LOG_DIR == "", "file logging stays off unless LOG_DIR says otherwise"
    assert settings.LOGGING["root"]["handlers"] == []
    assert "file" not in settings.LOGGING.get("handlers", {})


def test_development_writes_to_the_logs_folder(tmp_path: Path) -> None:
    report = settings_probe("config.settings.dev", LOG_DIR=str(tmp_path / "logs"))
    assert report["handlers"] == ["console", "file"]
    assert report["root"] == ["console", "file"]
    assert report["filename"].endswith("kuyash.log")


def test_development_can_switch_it_off() -> None:
    report = settings_probe("config.settings.dev", LOG_DIR="")
    assert "file" not in report["handlers"]


def test_development_defaults_to_the_backend_logs_folder() -> None:
    report = settings_probe("config.settings.dev")
    assert report["log_dir"] == str(BACKEND / "logs")


def test_production_logs_to_stdout_only() -> None:
    """A file inside a container is lost on deploy and can fill the disk."""
    report = settings_probe(
        "config.settings.prod",
        REDIS_URL="redis://localhost:6379/0",
        PAYSTACK_SECRET_KEY="sk_live_probe",
        SESSION_COOKIE_DOMAIN=".example.com",
        FRONTEND_URL="https://example.com",
        PAYMENT_CALLBACK_URL="https://example.com/checkout/complete",
        ACADEMY_PAYMENT_CALLBACK_URL="https://example.com/academy/complete",
    )
    assert report["handlers"] == ["console"]
    assert report["log_dir"] == ""
