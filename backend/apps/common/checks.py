"""Deployment checks derived from docs/SECURITY.md §8.

Django's own ``check --deploy`` covers the framework settings. These cover the
things specific to this system that would otherwise be a line on a checklist
somebody forgets to read.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.checks import Error, Warning, register


@register("kuyash", deploy=True)
def check_secrets_are_not_defaults(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Refuse to deploy with a development secret key."""
    issues: list[Any] = []
    weak = {"insecure-development-key", "test-only-key-not-secret", "changeme", ""}
    if settings.SECRET_KEY in weak or len(settings.SECRET_KEY) < 50:
        issues.append(
            Error(
                "DJANGO_SECRET_KEY is a placeholder or too short.",
                hint="Generate at least 50 random characters and store it in the secret manager.",
                id="kuyash.E010",
            )
        )
    return issues


@register("kuyash", deploy=True)
def check_cookie_domain_is_shared(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Session auth needs a shared parent domain (AUTH.md §2).

    Without it the cookie is never sent to the API and every login silently
    fails in production while working perfectly in development.
    """
    issues: list[Any] = []
    if not getattr(settings, "SESSION_COOKIE_DOMAIN", ""):
        issues.append(
            Warning(
                "SESSION_COOKIE_DOMAIN is not set.",
                hint=(
                    "Set it to the shared parent domain (e.g. .kuyashplace.com) or the "
                    "frontend will not be able to hold a session against the API."
                ),
                id="kuyash.W011",
            )
        )
    if not settings.CORS_ALLOW_CREDENTIALS:
        issues.append(
            Error(
                "CORS_ALLOW_CREDENTIALS is off, so the browser will not send the session cookie.",
                id="kuyash.E012",
            )
        )
    if "*" in settings.CORS_ALLOWED_ORIGINS:
        issues.append(
            Error(
                "CORS_ALLOWED_ORIGINS contains a wildcard alongside credentials.",
                hint="Browsers reject that combination; list the real origins.",
                id="kuyash.E013",
            )
        )
    return issues


@register("kuyash", deploy=True)
def check_payment_configuration(app_configs: Any, **kwargs: Any) -> list[Any]:
    """A site that can take orders must be able to charge for them."""
    issues: list[Any] = []
    if not (settings.PAYSTACK_SECRET_KEY or settings.FLUTTERWAVE_SECRET_KEY):
        issues.append(
            Error(
                "No payment provider is configured.",
                hint="Set PAYSTACK_SECRET_KEY or FLUTTERWAVE_SECRET_KEY.",
                id="kuyash.E014",
            )
        )
    if settings.PAYSTACK_SECRET_KEY.startswith("sk_test") or (
        settings.FLUTTERWAVE_SECRET_KEY.startswith("FLWSECK_TEST")
    ):
        issues.append(
            Warning(
                "A payment provider is configured with TEST keys.",
                hint="Live keys are required to take real money.",
                id="kuyash.W015",
            )
        )
    if not settings.PAYMENT_CALLBACK_URL.startswith("https://"):
        issues.append(
            Warning(
                "PAYMENT_CALLBACK_URL is not https.",
                id="kuyash.W016",
            )
        )
    return issues


@register("kuyash", deploy=True)
def check_background_processing(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Eager Celery in production means the reconciliation sweep never runs.

    That sweep is the safety net for a webhook that never arrived — without it,
    a customer can pay and never be acknowledged.
    """
    issues: list[Any] = []
    if settings.CELERY_TASK_ALWAYS_EAGER:
        issues.append(
            Error(
                "CELERY_TASK_ALWAYS_EAGER is on, so scheduled work never runs.",
                hint=(
                    "payments.verify_pending is the safety net for missed payment "
                    "webhooks. Configure REDIS_URL and run a worker and beat."
                ),
                id="kuyash.E017",
            )
        )
    if not settings.CELERY_BEAT_SCHEDULE:
        issues.append(Warning("No Celery beat schedule is configured.", id="kuyash.W018"))
    return issues


@register("kuyash", deploy=True)
def check_admin_is_not_on_the_default_path(app_configs: Any, **kwargs: Any) -> list[Any]:
    """AS-7: a default admin path invites automated credential stuffing."""
    if settings.ADMIN_URL.strip("/") == "admin":
        return [
            Warning(
                "The Django admin is on its default path.",
                hint="Set ADMIN_URL to something non-guessable and restrict it by IP or VPN.",
                id="kuyash.W019",
            )
        ]
    return []


@register("kuyash", deploy=True)
def check_email_is_configured(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Verification and order confirmations both depend on email."""
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if "console" in backend or "locmem" in backend:
        return [
            Error(
                "Email is configured to a development backend, so nothing is delivered.",
                hint="Customers would never receive verification or order confirmations.",
                id="kuyash.E020",
            )
        ]
    return []
