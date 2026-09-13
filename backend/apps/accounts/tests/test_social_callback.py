"""Where Google and Facebook may send the customer back to.

The frontend runs on a different origin from the API. allauth accepts a social
`callback_url` only when its host is in ALLOWED_HOSTS or CSRF_TRUSTED_ORIGINS, so
removing the frontend from CSRF_TRUSTED_ORIGINS would break social sign-in with
nothing but an `invalid_url` error on the provider redirect. These tests pin it,
and pin that a foreign callback — an open redirect — stays refused.
"""

from __future__ import annotations

import pytest
from allauth.account.adapter import get_adapter
from allauth.core import context
from django.test import RequestFactory, override_settings

pytestmark = pytest.mark.django_db

FRONTEND = "http://localhost:3000"


def is_safe(url: str) -> bool:
    request = RequestFactory().post(
        "/_allauth/browser/v1/auth/provider/redirect", HTTP_HOST="localhost"
    )
    with context.request_context(request):
        return bool(get_adapter().is_safe_url(url))


@override_settings(CSRF_TRUSTED_ORIGINS=[FRONTEND], ALLOWED_HOSTS=["localhost", "testserver"])
def test_the_frontend_callback_is_accepted() -> None:
    assert is_safe(f"{FRONTEND}/auth/callback?next=/account") is True


@override_settings(CSRF_TRUSTED_ORIGINS=[FRONTEND], ALLOWED_HOSTS=["localhost", "testserver"])
def test_a_foreign_callback_is_refused() -> None:
    assert is_safe("https://evil.example/auth/callback") is False


@override_settings(CSRF_TRUSTED_ORIGINS=[], ALLOWED_HOSTS=["localhost", "testserver"])
def test_without_the_frontend_origin_the_callback_is_refused() -> None:
    """The failure mode this file exists to make visible."""
    assert is_safe(f"{FRONTEND}/auth/callback") is False
