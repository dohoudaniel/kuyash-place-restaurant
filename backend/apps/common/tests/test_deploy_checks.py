"""Deployment checks.

These are the launch gate from docs/SECURITY.md §8. A check that does not fire
when it should is worse than no check, because it reads as assurance.
"""

from __future__ import annotations

import pytest
from django.core.checks import Error, Warning
from django.test import override_settings

from apps.common.checks import (
    check_admin_is_not_on_the_default_path,
    check_background_processing,
    check_cookie_domain_is_shared,
    check_email_is_configured,
    check_payment_configuration,
    check_secrets_are_not_defaults,
)

GOOD_SECRET = "x" * 60


def ids(issues: list) -> set[str]:  # type: ignore[type-arg]
    return {issue.id for issue in issues}


# ── Secret key ────────────────────────────────────────────────────────────────


@override_settings(SECRET_KEY="insecure-development-key")
def test_a_placeholder_secret_key_blocks_deployment() -> None:
    assert "kuyash.E010" in ids(check_secrets_are_not_defaults(None))


@override_settings(SECRET_KEY="short")
def test_a_short_secret_key_blocks_deployment() -> None:
    assert "kuyash.E010" in ids(check_secrets_are_not_defaults(None))


@override_settings(SECRET_KEY=GOOD_SECRET)
def test_a_strong_secret_key_passes() -> None:
    assert check_secrets_are_not_defaults(None) == []


# ── Cookies and CORS ──────────────────────────────────────────────────────────


@override_settings(
    SESSION_COOKIE_DOMAIN="",
    CORS_ALLOW_CREDENTIALS=True,
    CORS_ALLOWED_ORIGINS=["https://kuyashplace.com"],
)
def test_a_missing_cookie_domain_warns() -> None:
    """Without it every login works locally and silently fails in production."""
    assert "kuyash.W011" in ids(check_cookie_domain_is_shared(None))


@override_settings(
    SESSION_COOKIE_DOMAIN=".kuyashplace.com",
    CORS_ALLOW_CREDENTIALS=False,
    CORS_ALLOWED_ORIGINS=["https://kuyashplace.com"],
)
def test_credentials_disabled_blocks_deployment() -> None:
    assert "kuyash.E012" in ids(check_cookie_domain_is_shared(None))


@override_settings(
    SESSION_COOKIE_DOMAIN=".kuyashplace.com",
    CORS_ALLOW_CREDENTIALS=True,
    CORS_ALLOWED_ORIGINS=["*"],
)
def test_a_cors_wildcard_with_credentials_blocks_deployment() -> None:
    """Browsers reject that combination outright."""
    assert "kuyash.E013" in ids(check_cookie_domain_is_shared(None))


@override_settings(
    SESSION_COOKIE_DOMAIN=".kuyashplace.com",
    CORS_ALLOW_CREDENTIALS=True,
    CORS_ALLOWED_ORIGINS=["https://kuyashplace.com"],
)
def test_a_correct_cookie_setup_passes() -> None:
    assert check_cookie_domain_is_shared(None) == []


# ── Payments ──────────────────────────────────────────────────────────────────


@override_settings(
    PAYSTACK_SECRET_KEY="", FLUTTERWAVE_SECRET_KEY="", PAYMENT_CALLBACK_URL="https://x/complete"
)
def test_no_provider_blocks_deployment() -> None:
    """A site that can take orders must be able to charge for them."""
    assert "kuyash.E014" in ids(check_payment_configuration(None))


@override_settings(
    PAYSTACK_SECRET_KEY="sk_test_abc",
    FLUTTERWAVE_SECRET_KEY="",
    PAYMENT_CALLBACK_URL="https://x/complete",
)
def test_test_keys_warn() -> None:
    assert "kuyash.W015" in ids(check_payment_configuration(None))


@override_settings(
    PAYSTACK_SECRET_KEY="sk_live_abc",
    FLUTTERWAVE_SECRET_KEY="",
    PAYMENT_CALLBACK_URL="http://insecure/complete",
)
def test_an_insecure_callback_url_warns() -> None:
    assert "kuyash.W016" in ids(check_payment_configuration(None))


@override_settings(
    PAYSTACK_SECRET_KEY="sk_live_abc",
    FLUTTERWAVE_SECRET_KEY="",
    PAYMENT_CALLBACK_URL="https://x/complete",
)
def test_live_payment_configuration_passes() -> None:
    assert check_payment_configuration(None) == []


# ── Background processing ─────────────────────────────────────────────────────


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_BEAT_SCHEDULE={"x": {}})
def test_eager_celery_blocks_deployment() -> None:
    """Eager Celery means the payment reconciliation sweep never runs — a
    customer could pay and never be acknowledged."""
    issues = check_background_processing(None)
    assert "kuyash.E017" in ids(issues)
    assert any(isinstance(issue, Error) for issue in issues)


@override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BEAT_SCHEDULE={})
def test_a_missing_beat_schedule_warns() -> None:
    issues = check_background_processing(None)
    assert "kuyash.W018" in ids(issues)
    assert all(isinstance(issue, Warning) for issue in issues)


@override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BEAT_SCHEDULE={"x": {}})
def test_correct_background_configuration_passes() -> None:
    assert check_background_processing(None) == []


# ── Admin path ────────────────────────────────────────────────────────────────


@override_settings(ADMIN_URL="admin/")
def test_the_default_admin_path_warns() -> None:
    assert "kuyash.W019" in ids(check_admin_is_not_on_the_default_path(None))


@override_settings(ADMIN_URL="ops-7f3a/")
def test_a_non_default_admin_path_passes() -> None:
    assert check_admin_is_not_on_the_default_path(None) == []


# ── Email ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "backend",
    [
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
    ],
)
def test_a_development_email_backend_blocks_deployment(backend: str) -> None:
    """Customers would never receive verification or order confirmations."""
    with override_settings(EMAIL_BACKEND=backend):
        assert "kuyash.E020" in ids(check_email_is_configured(None))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
def test_a_real_email_backend_passes() -> None:
    assert check_email_is_configured(None) == []
