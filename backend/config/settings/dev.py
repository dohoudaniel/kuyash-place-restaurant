"""Local development settings.

Deliberately dependency-free: SQLite, in-memory cache, eager Celery, console email.
Point DATABASE_URL / REDIS_URL at real services when you want them.
"""

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed for local work only. Never set these in prod.py.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Verification emails are printed to the console in development.
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="optional")

INTERNAL_IPS = ["127.0.0.1"]
