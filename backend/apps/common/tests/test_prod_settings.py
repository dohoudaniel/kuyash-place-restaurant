"""The real production settings module, loaded as a deploy would load it (SECURITY.md §8).

The test suite runs on ``config.settings.test``, so nothing else proves that
``config.settings.prod`` turns DEBUG off, needs explicit hosts, sends HSTS and
passes ``check --deploy``. Each case runs in a fresh interpreter with a
production-shaped environment, because settings are read once per process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[3]

PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "prod-shaped-test-key-not-a-secret-but-long-and-varied-0123456789-XyZ",
    "ALLOWED_HOSTS": "api.kuyashplace.com",
    "DATABASE_URL": "sqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
    "PAYSTACK_SECRET_KEY": "sk_live_placeholder_for_settings_test",
    "ADMIN_URL": "staff-console-3b9e/",
    "TRUSTED_PROXY_COUNT": "1",
    "SESSION_COOKIE_DOMAIN": ".kuyashplace.com",
    "FRONTEND_URL": "https://kuyashplace.com",
    "PAYMENT_CALLBACK_URL": "https://kuyashplace.com/checkout/complete",
    "ACADEMY_PAYMENT_CALLBACK_URL": "https://kuyashplace.com/academy/enrolment/complete",
}

PROBE = """
import json, django
django.setup()
from django.conf import settings as s
print(json.dumps({
    "DEBUG": s.DEBUG,
    "ALLOWED_HOSTS": s.ALLOWED_HOSTS,
    "SECURE_HSTS_SECONDS": s.SECURE_HSTS_SECONDS,
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": s.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "SECURE_SSL_REDIRECT": s.SECURE_SSL_REDIRECT,
    "SESSION_COOKIE_SECURE": s.SESSION_COOKIE_SECURE,
    "CSRF_COOKIE_SECURE": s.CSRF_COOKIE_SECURE,
    "X_FRAME_OPTIONS": s.X_FRAME_OPTIONS,
    "STAFF_MFA_REQUIRED": s.STAFF_MFA_REQUIRED,
    "CELERY_TASK_ALWAYS_EAGER": s.CELERY_TASK_ALWAYS_EAGER,
}))
"""


def run(args: list[str], **overrides: str | None) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("DJANGO_")}
    env.update(PRODUCTION_ENV)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(  # noqa: S603 - fixed argv, this interpreter
        [sys.executable, *args], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120
    )


@pytest.fixture(scope="module")
def prod() -> dict[str, object]:
    result = run(["-c", PROBE])
    assert result.returncode == 0, result.stderr
    return dict(json.loads(result.stdout.strip().splitlines()[-1]))


def test_debug_is_off(prod) -> None:  # type: ignore[no-untyped-def]
    assert prod["DEBUG"] is False


def test_allowed_hosts_are_exactly_what_was_configured(prod) -> None:  # type: ignore[no-untyped-def]
    assert prod["ALLOWED_HOSTS"] == ["api.kuyashplace.com"]


def test_https_is_enforced_with_hsts(prod) -> None:  # type: ignore[no-untyped-def]
    assert prod["SECURE_HSTS_SECONDS"] >= 31_536_000  # type: ignore[operator]
    assert prod["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert prod["SECURE_SSL_REDIRECT"] is True
    assert prod["SESSION_COOKIE_SECURE"] is True
    assert prod["CSRF_COOKIE_SECURE"] is True
    assert prod["X_FRAME_OPTIONS"] == "DENY"


def test_staff_two_factor_and_real_workers_are_on(prod) -> None:  # type: ignore[no-untyped-def]
    assert prod["STAFF_MFA_REQUIRED"] is True
    assert prod["CELERY_TASK_ALWAYS_EAGER"] is False


@pytest.mark.parametrize(
    "missing", ["DJANGO_SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL", "REDIS_URL"]
)
def test_a_missing_required_variable_stops_the_process(missing: str) -> None:
    result = run(["-c", PROBE], **{missing: None})
    assert result.returncode != 0
    assert missing.replace("DJANGO_", "") in result.stderr or "REDIS_URL" in result.stderr


def test_the_deploy_check_is_clean_at_warning_level() -> None:
    result = run(["manage.py", "check", "--deploy", "--fail-level", "WARNING"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no issues" in result.stdout
