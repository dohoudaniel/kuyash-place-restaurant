"""Test settings: fast, hermetic, no external services."""

from .base import *

DEBUG = False
SECRET_KEY = "test-only-key-not-secret"  # noqa: S105

# SQLite in memory by default for speed. CI also runs this suite with
# DATABASE_URL pointing at Postgres, which is where the concurrency tests and
# Postgres-only query paths actually execute (ADR-015).
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db_url("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
USING_POSTGRES = "postgresql" in DATABASES["default"]["ENGINE"]

# Fast hashing — tests create a lot of users.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Throttling off by default. Views declare explicit throttle_classes, so simply
# emptying DEFAULT_THROTTLE_CLASSES is not enough — the rates themselves must be
# None, which makes SimpleRateThrottle a no-op. Tests that exercise throttling
# re-enable a specific scope with override_settings.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": dict.fromkeys(REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]),
}

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]

LOGGING = {"version": 1, "disable_existing_loggers": True, "root": {"handlers": []}}
