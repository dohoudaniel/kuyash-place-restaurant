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

# Verification stays MANDATORY in development, matching test and production.
# An earlier revision defaulted this to "optional" as a convenience, which meant
# local testing never exercised the real sign-in path — exactly the dev/prod
# divergence that ships "works on my machine" bugs. The confirmation link is
# printed to the console and recorded in the notifications outbox, so there is
# no friction to justify diverging.
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="mandatory")

INTERNAL_IPS = ["127.0.0.1"]
