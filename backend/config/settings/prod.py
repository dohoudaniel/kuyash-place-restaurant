"""Production settings.

Fails loudly at import time on any missing required variable — a misconfigured
deploy stops immediately rather than at the first customer order.
"""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

DEBUG = False

# Required — env() without a default raises ImproperlyConfigured when absent.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
DATABASES = {"default": env.db_url("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
USING_POSTGRES = "postgresql" in DATABASES["default"]["ENGINE"]

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required in production.")

CELERY_TASK_ALWAYS_EAGER = False

# ── Transport security ────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# At least one payment provider must be configured, or the site can take orders
# it cannot charge for. A missing key is an error, never a quiet downgrade to
# the simulated provider.
if not (PAYSTACK_SECRET_KEY or FLUTTERWAVE_SECRET_KEY):
    raise RuntimeError("Configure PAYSTACK_SECRET_KEY or FLUTTERWAVE_SECRET_KEY before deploying.")

LOG_FORMAT = "json"
LOGGING["handlers"]["console"]["formatter"] = "json"  # type: ignore[index]

# ── Sentry ────────────────────────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,  # SECURITY.md §6
        before_send=lambda event, hint: __import__(
            "apps.common.observability", fromlist=["scrub_event"]
        ).scrub_event(event, hint),
    )
