"""Local development settings.

Deliberately dependency-free: SQLite, in-memory cache, eager Celery, console email.
Point DATABASE_URL / REDIS_URL at real services when you want them.
"""

from apps.common.logging import file_handler

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed for local work only. Never set these in prod.py.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Verification stays MANDATORY in development, matching test and production.
# An earlier revision defaulted this to "optional" as a convenience, which meant
# local testing never exercised the real sign-in path — exactly the dev/prod
# divergence that ships "works on my machine" bugs. The confirmation link is
# printed to the console and recorded in the notifications outbox, so there is
# no friction to justify diverging.
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="mandatory")

INTERNAL_IPS = ["127.0.0.1"]

# ── Logs on disk ──────────────────────────────────────────────────────────────
# Locally there is no platform collecting stdout, and the terminal scrolls away,
# so development also writes backend/logs/kuyash.log (rotating, 5 MB × 5). The
# folder is git-ignored. Set LOG_DIR= (empty) in .env to switch it off, or point
# it somewhere else. Deployed environments leave LOG_DIR unset.
LOG_DIR = env("LOG_DIR", default=str(BASE_DIR / "logs"))
_dev_log_file = file_handler(
    LOG_DIR,
    formatter=LOG_FILE_FORMAT,
    max_bytes=LOG_FILE_MAX_BYTES,
    backups=LOG_FILE_BACKUPS,
)
if _dev_log_file is not None:
    LOGGING["handlers"]["file"] = _dev_log_file
    if "file" not in LOGGING["root"]["handlers"]:
        LOGGING["root"]["handlers"] = [*LOGGING["root"]["handlers"], "file"]
