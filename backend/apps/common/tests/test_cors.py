"""Cross-origin headers the frontend depends on.

The frontend runs on its own origin and sends custom headers. If a preflight does
not allow a header, the browser refuses to send the request at all — the backend
never sees it, so no view test can catch the omission.
"""

from __future__ import annotations

import pytest
from django.test import Client, override_settings

FRONTEND = "http://localhost:3000"

pytestmark = pytest.mark.django_db


def preflight(path: str, headers: str) -> dict[str, str]:
    response = Client().options(
        path,
        HTTP_ORIGIN=FRONTEND,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS=headers,
    )
    return {key.lower(): value for key, value in response.items()}


@override_settings(CORS_ALLOWED_ORIGINS=[FRONTEND])
@pytest.mark.parametrize(
    "header",
    [
        "x-cart-token",
        "x-guest-token",
        "x-chat-token",
        "x-enrolment-token",
        "idempotency-key",
        "x-csrftoken",
        "content-type",
    ],
)
def test_preflight_allows_every_header_the_client_sends(header: str) -> None:
    allowed = preflight("/api/v1/orders/", header).get("access-control-allow-headers", "")
    assert header in {h.strip().lower() for h in allowed.split(",")}


@override_settings(CORS_ALLOWED_ORIGINS=[FRONTEND])
def test_preflight_allows_credentials_for_the_frontend() -> None:
    headers = preflight("/api/v1/auth/login/", "content-type")
    assert headers.get("access-control-allow-origin") == FRONTEND
    assert headers.get("access-control-allow-credentials") == "true"


@override_settings(CORS_ALLOWED_ORIGINS=[FRONTEND])
def test_the_cart_token_can_be_read_back_by_the_browser() -> None:
    """Exposed, or the client can never store the anonymous cart's token."""
    response = Client().get("/api/v1/auth/session/", HTTP_ORIGIN=FRONTEND)
    exposed = response.get("Access-Control-Expose-Headers", "").lower()
    assert "x-cart-token" in exposed
