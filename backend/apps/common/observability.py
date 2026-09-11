"""Sentry scrubbing.

Belt and braces alongside ``send_default_pii=False``: strip anything that looks
like a credential or cardholder value before an event leaves the process.
"""

from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "token",
    "guest_token",
    "secret",
    "authorization",
    "csrftoken",
    "sessionid",
    "card",
    "cardnumber",
    "card_number",
    "cvv",
    "cardcvv",
    "card_cvv",
    "pan",
    "authorization_code",
    "api_key",
    "secret_key",
}

REDACTED = "[redacted]"


def _scrub(value: Any, depth: int = 0) -> Any:
    if depth > 12:
        return value
    if isinstance(value, dict):
        return {
            key: (REDACTED if str(key).lower() in SENSITIVE_KEYS else _scrub(item, depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item, depth + 1) for item in value]
    return value


def scrub_event(event: dict[str, Any], hint: Any) -> dict[str, Any]:
    """``before_send`` hook for Sentry."""
    return _scrub(event)
