"""Auth throttling.

Login and password reset are throttled per IP **and** per account (AS-4).
Per-IP alone lets a botnet spread an attack across addresses; per-account alone
lets one IP spray many accounts.
"""

from __future__ import annotations

from typing import Any

from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView


class _EmailKeyedThrottle(SimpleRateThrottle):
    """Throttles on the submitted email rather than the caller's address."""

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        email = ""
        if isinstance(request.data, dict):
            email = str(request.data.get("email", "")).lower().strip()
        if not email:
            return None  # nothing to key on; the IP throttle still applies
        return self.cache_format % {"scope": self.scope, "ident": email}


class LoginIPThrottle(AnonRateThrottle):
    scope = "login"


class LoginEmailThrottle(_EmailKeyedThrottle):
    scope = "login_email"


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class PasswordResetIPThrottle(AnonRateThrottle):
    scope = "password_reset"


class PasswordResetEmailThrottle(_EmailKeyedThrottle):
    scope = "password_reset_email"


class ResendVerificationThrottle(_EmailKeyedThrottle):
    scope = "resend_verification"


__all__: list[Any] = [
    "LoginEmailThrottle",
    "LoginIPThrottle",
    "PasswordResetEmailThrottle",
    "PasswordResetIPThrottle",
    "RegisterThrottle",
    "ResendVerificationThrottle",
]
