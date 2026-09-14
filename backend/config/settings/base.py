"""Settings shared by every environment.

Environment-specific modules (dev/test/prod) import * from here and override.
Nothing in this file may assume a particular deployment target.
"""

from __future__ import annotations

from pathlib import Path

import environ
from corsheaders.defaults import default_headers as default_cors_headers

from apps.common.storage import supabase_public_domain

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ── Identity ──────────────────────────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-development-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# ── Applications ──────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "storages",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.core",
    "apps.catalog",
    "apps.delivery",
    "apps.promotions",
    "apps.carts",
    "apps.orders",
    "apps.payments",
    "apps.reservations",
    "apps.catering",
    "apps.support",
    "apps.notifications",
    "apps.reviews",
    "apps.gallery",
    "apps.academy",
    "apps.loyalty",
    "apps.reporting",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── Database ──────────────────────────────────────────────────────────────────
# Local development defaults to SQLite so that no database server is required.
# Set DATABASE_URL to a Postgres URL for staging/production (and locally, if you
# have Postgres running). Postgres-only features (GIN indexes, ExclusionConstraint)
# arrive in Phase 1/2 and are guarded by the `USING_POSTGRES` flag below.
DATABASES = {
    "default": env.db_url("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
DATABASES["default"].setdefault("ATOMIC_REQUESTS", False)
USING_POSTGRES = "postgresql" in DATABASES["default"]["ENGINE"]
if USING_POSTGRES:
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Authentication ────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Argon2 first — see SECURITY.md AS-9.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── allauth ───────────────────────────────────────────────────────────────────
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3

# How long a customer may edit a review after posting it (REV-5).
REVIEW_EDIT_WINDOW_DAYS = env.int("REVIEW_EDIT_WINDOW_DAYS", default=7)
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = "apps.accounts.adapters.KuyashAccountAdapter"

# Throttled per IP *and* per account (SECURITY.md AS-4). "5/5m" is five attempts
# per five minutes; the key suffix picks what the bucket is keyed on.
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/5m/ip,10/h/key",
    "signup": "3/h/ip",
    "reset_password": "3/h/ip,3/h/key",
    "reset_password_from_key": "5/h/ip",
    "confirm_email": "3/m/key",
    "change_password": "5/h/user",
}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour — matches the copy already shown in the UI

# ── Social login ──────────────────────────────────────────────────────────────
# Wires up the two buttons that currently say
# alert("Google login - Integration needed").
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.KuyashSocialAdapter"
SOCIALACCOUNT_STORE_TOKENS = False  # we never act on the customer's behalf
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True

# Sign in an existing account when the provider asserts a *verified* email.
# Without this a customer who registered with a password and later clicks
# "Continue with Google" gets a confusing duplicate-email error. With it, the
# provider's verification is what links them — which is why it must only ever
# apply to providers that actually verify.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        # Google asserts email_verified; allauth honours it.
        "EMAIL_AUTHENTICATION": True,
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
        "FIELDS": ["id", "email", "name", "first_name", "last_name"],
        "VERIFIED_EMAIL": False,
        # Facebook's email assertion is less reliable, so it does NOT
        # auto-link to an existing password account (AUTH.md §4.4).
        "EMAIL_AUTHENTICATION": False,
    },
}

# Credentials are attached only when they exist. allauth lists every provider
# that has an APP entry — even one with a blank client_id — so an unconfigured
# provider would still appear in /_allauth/browser/v1/config, the frontend would
# render its button, and the customer would land on an error page. With no
# credentials the provider is simply absent and its button is never shown.
for _provider, _prefix in (("google", "GOOGLE"), ("facebook", "FACEBOOK")):
    _client_id = env(f"{_prefix}_CLIENT_ID", default="")
    if _client_id:
        SOCIALACCOUNT_PROVIDERS[_provider]["APP"] = {
            "client_id": _client_id,
            "secret": env(f"{_prefix}_CLIENT_SECRET", default=""),
            "key": "",
        }

HEADLESS_ONLY = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": FRONTEND_URL + "/verify-email?key={key}",
    "account_reset_password": FRONTEND_URL + "/reset-password",
    "account_reset_password_from_key": FRONTEND_URL + "/reset-password?key={key}",
    "account_signup": FRONTEND_URL + "/signup",
    # Where allauth sends the browser when social sign-in fails: the customer
    # cancelled at Google, the provider errored, or the takeover backstop refused
    # an unverified email. allauth appends ?error=…. Without this entry every one
    # of those failures raised ImproperlyConfigured and the customer saw a 500.
    "socialaccount_login_error": FRONTEND_URL + "/auth/callback",
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Endpoints opt in to protection explicitly; most of the catalogue is public.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.problem_detail_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/min",
        "user": "300/min",
        "login": "5/min",
        "login_email": "10/hour",
        "register": "3/hour",
        "password_reset": "3/hour",
        "password_reset_email": "3/hour",
        "resend_verification": "3/hour",
        "order_create": "10/hour",
        "promo_apply": "10/min",
        "contact": "3/hour",
        "catering": "5/hour",
        "review_create": "10/hour",
        "review_vote": "60/hour",
        "chat_session": "20/hour",
        "chat_message": "30/min",
        "chat_escalate": "3/hour",
        "enrolment_create": "10/hour",
    },
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Kuyash Place Restaurant API",
    "DESCRIPTION": (
        "Backend API for Kuyash Place Restaurant.\n\n"
        "**All money values are integer kobo** wrapped in a `{amount, currency, display}` "
        "object. Clients render `display` and never perform arithmetic on `amount`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    # Every app has a `status` field with its own choices. Without explicit names
    # drf-spectacular emits hash-suffixed enums (`Status889Enum`) whose names
    # change whenever a choice set does — and the frontend's generated types
    # would churn with them.
    "ENUM_NAME_OVERRIDES": {
        "OrderStatusEnum": "apps.orders.models.OrderStatus",
        "PaymentStatusEnum": "apps.orders.models.PaymentStatus",
        "CartStatusEnum": "apps.carts.models.CartStatus",
        "ReservationStatusEnum": "apps.reservations.models.ReservationStatus",
        "EnquiryStatusEnum": "apps.catering.models.EnquiryStatus",
        "TicketStatusEnum": "apps.support.models.TicketStatus",
        "TransactionStatusEnum": "apps.payments.models.TransactionStatus",
        "RefundStatusEnum": "apps.payments.models.RefundStatus",
        "RedemptionStatusEnum": "apps.promotions.models.RedemptionStatus",
        "NotificationStatusEnum": "apps.notifications.models.NotificationStatus",
        "ReviewStatusEnum": "apps.reviews.models.ReviewStatus",
        "GalleryCategoryEnum": "apps.gallery.models.GalleryCategory",
        "ChatSenderEnum": "apps.support.models.ChatSender",
        "CourseLevelEnum": "apps.academy.models.CourseLevel",
        "CourseTypeEnum": "apps.academy.models.CourseType",
        "CohortStatusEnum": "apps.academy.models.CohortStatus",
        "EnrolmentStatusEnum": "apps.academy.models.EnrolmentStatus",
        "ExperienceLevelEnum": "apps.academy.models.ExperienceLevel",
        "EnrolmentPaymentMethodEnum": "apps.academy.models.EnrolmentPaymentMethod",
        "LedgerEntryTypeEnum": "apps.loyalty.models.LedgerEntryType",
        "RewardTypeEnum": "apps.loyalty.models.RewardType",
    },
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"  # storage is UTC; business hours use BUSINESS_TIME_ZONE
BUSINESS_TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# ── Static & media ────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

_SUPABASE_ENDPOINT = env("SUPABASE_S3_ENDPOINT", default="")
if _SUPABASE_ENDPOINT:
    # Supabase Storage exposes an S3-compatible API; see DEPLOYMENT.md §5.
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    AWS_S3_ENDPOINT_URL = _SUPABASE_ENDPOINT
    AWS_STORAGE_BUCKET_NAME = env("SUPABASE_BUCKET")
    AWS_S3_REGION_NAME = env("SUPABASE_REGION", default="eu-west-1")
    AWS_ACCESS_KEY_ID = env("SUPABASE_S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = env("SUPABASE_S3_SECRET_KEY")
    AWS_S3_ADDRESSING_STYLE = "path"  # Supabase requires path-style addressing
    # Reads must use the public object URL, not the S3 endpoint the writes go
    # through — see apps/common/storage.py for why the difference matters.
    AWS_S3_CUSTOM_DOMAIN = supabase_public_domain(
        _SUPABASE_ENDPOINT, AWS_STORAGE_BUCKET_NAME, env("SUPABASE_PUBLIC_URL", default="")
    )
    AWS_QUERYSTRING_AUTH = False  # menu and gallery images are public
    AWS_S3_FILE_OVERWRITE = False
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# ── Cache ─────────────────────────────────────────────────────────────────────
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    # No Redis locally: in-memory cache keeps development dependency-free.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kuyash-local",
        }
    }

# ── Celery ────────────────────────────────────────────────────────────────────
# Without Redis, tasks run eagerly (synchronously, in-process). That keeps local
# development to a single process; see DEPLOYMENT.md §2.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=not REDIS_URL)
CELERY_TASK_EAGER_PROPAGATES = True
# "memory://localhost//" rather than "memory://": kombu warns about a missing
# hostname on the bare form even when tasks run eagerly and never connect.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "memory://localhost//")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL or "cache+memory://")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

# Scheduled work. `verify_pending` is the safety net for a webhook that never
# arrived; see apps/payments/tasks.py.
CELERY_BEAT_SCHEDULE = {
    "verify-pending-payments": {
        "task": "payments.verify_pending",
        "schedule": 600.0,  # every 10 minutes
    },
    "expire-stale-orders": {
        "task": "payments.expire_stale_orders",
        "schedule": 3600.0,  # hourly
    },
    "loyalty-birthday-bonuses": {
        "task": "loyalty.birthday_bonuses",
        "schedule": 86400.0,  # daily; idempotent per member per year
    },
    "loyalty-expire-inactive": {
        "task": "loyalty.expire_inactive",
        "schedule": 86400.0,  # daily
    },
}

# ── Sessions & CSRF ───────────────────────────────────────────────────────────
SESSION_COOKIE_NAME = "kuyash_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_SAVE_EVERY_REQUEST = True

CSRF_COOKIE_NAME = "kuyash_csrftoken"
CSRF_COOKIE_HTTPONLY = False  # the frontend must read this to echo it back
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["X-Cart-Token", "X-Request-ID", "Idempotency-Replayed"]
# The frontend *sends* these on cross-origin requests, so the preflight must allow
# them. Without this the browser blocks every request once a cart token exists,
# and every order placement (Idempotency-Key) — found by the first live run of the
# frontend client, not by any unit test.
CORS_ALLOW_HEADERS = (
    *default_cors_headers,
    "x-cart-token",
    "x-guest-token",
    "x-chat-token",
    "x-enrolment-token",
    "idempotency-key",
)

_SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default="")
if _SESSION_COOKIE_DOMAIN:
    SESSION_COOKIE_DOMAIN = _SESSION_COOKIE_DOMAIN
    CSRF_COOKIE_DOMAIN = _SESSION_COOKIE_DOMAIN

# ── Email ─────────────────────────────────────────────────────────────────────
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Kuyash Place <orders@kuyashplace.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── Uploads ───────────────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ── Admin ─────────────────────────────────────────────────────────────────────
# Non-default path in production (SECURITY.md AS-7).
ADMIN_URL = env("ADMIN_URL", default="admin/")
ADMIN_SITE_HEADER = "Kuyash Place"
ADMIN_SITE_TITLE = "Kuyash Place admin"
ADMIN_INDEX_TITLE = "Restaurant administration"

# ── Payments ──────────────────────────────────────────────────────────────────
# Secret keys are server-side only and must never appear in a NEXT_PUBLIC_*
# variable. Only the PUBLIC keys are safe to hand to a browser.
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_PUBLIC_KEY = env("PAYSTACK_PUBLIC_KEY", default="")
FLUTTERWAVE_SECRET_KEY = env("FLUTTERWAVE_SECRET_KEY", default="")
FLUTTERWAVE_PUBLIC_KEY = env("FLUTTERWAVE_PUBLIC_KEY", default="")
FLUTTERWAVE_WEBHOOK_SECRET_HASH = env("FLUTTERWAVE_WEBHOOK_SECRET_HASH", default="")
DEFAULT_PAYMENT_PROVIDER = env("DEFAULT_PAYMENT_PROVIDER", default="paystack")
PAYMENT_CALLBACK_URL = env("PAYMENT_CALLBACK_URL", default=f"{FRONTEND_URL}/checkout/complete")
ACADEMY_PAYMENT_CALLBACK_URL = env(
    "ACADEMY_PAYMENT_CALLBACK_URL", default=f"{FRONTEND_URL}/academy/enrolment/complete"
)
# An unpaid enrolment holds its seat this long, so a cohort cannot be filled by
# people who never pay.
ACADEMY_CARD_HOLD_MINUTES = env.int("ACADEMY_CARD_HOLD_MINUTES", default=30)
ACADEMY_TRANSFER_HOLD_HOURS = env.int("ACADEMY_TRANSFER_HOLD_HOURS", default=48)

# Kuyash Rewards (LOY-2): kobo spent per base point (10_000 = 1 point per ₦100),
# and how long a balance survives without an order or a redemption.
LOYALTY_KOBO_PER_POINT = env.int("LOYALTY_KOBO_PER_POINT", default=10_000)
LOYALTY_EXPIRY_INACTIVE_DAYS = env.int("LOYALTY_EXPIRY_INACTIVE_DAYS", default=365)

# ── Domain defaults ───────────────────────────────────────────────────────────
DEFAULT_CURRENCY = "NGN"
DEFAULT_VAT_RATE_BPS = 750  # 7.5%

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="console")  # "console" or "json"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.common.logging.RequestIDFilter"},
    },
    "formatters": {
        "console": {
            "format": "{levelname:<8} {asctime} {name} [{request_id}] {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(levelname)s %(asctime)s %(name)s %(request_id)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": LOG_FORMAT,
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "propagate": True},
        "apps": {"level": LOG_LEVEL, "propagate": True},
    },
}
