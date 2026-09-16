"""Auth defects found by running the frontend against a live server.

None of these were visible to the existing unit tests: each needed a real
browser-shaped interaction — a signed-in visitor resetting a password, a request
without a CSRF token, a click on "Continue with Google".
"""

from __future__ import annotations

import re

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db

GOOGLE_APP = {
    "google": {
        "SCOPE": ["profile", "email"],
        "APP": {"client_id": "test-client-id.apps.googleusercontent.com", "secret": "s", "key": ""},
    }
}


def reset_link_parts(client: APIClient, email: str) -> tuple[str, str]:
    client.post(reverse("v1:auth:password-reset"), {"email": email}, format="json")
    body = Notification.objects.filter(template_key="password_reset").latest("created_at").body
    match = re.search(r"uid=([^&]+)&token=([^\s]+)", body)
    assert match
    return match.group(1), match.group(2)


# ── Password reset while signed in ────────────────────────────────────────────


def test_a_signed_in_visitor_can_reset_their_password(verified_user: User) -> None:
    """Previously: password changed, then an HTML 400 because the request's own
    session had been deleted underneath the session middleware."""
    client = APIClient()
    client.force_login(verified_user)
    uid, token = reset_link_parts(client, verified_user.email)

    response = client.post(
        reverse("v1:auth:password-reset-confirm"),
        {"uid": uid, "token": token, "new_password": "a-brand-new-long-passphrase"},
        format="json",
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert client.get(reverse("v1:auth:session")).json()["user"] is None
    verified_user.refresh_from_db()
    assert verified_user.check_password("a-brand-new-long-passphrase")


def test_a_weak_new_password_is_reported_as_json(
    api_client: APIClient, verified_user: User
) -> None:
    """A rejected password gets its own code.

    It used to share ``invalid_token`` with a dead link, so the frontend had to
    regex the prose to decide between "request a new link" and "pick a stronger
    password" — in a codebase whose contract is to branch on the code.
    """
    uid, token = reset_link_parts(api_client, verified_user.email)
    response = api_client.post(
        reverse("v1:auth:password-reset-confirm"),
        {"uid": uid, "token": token, "new_password": "1234567890"},
        format="json",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "weak_password"
    assert "numeric" in body["detail"].lower() or "common" in body["detail"].lower()


def test_a_dead_reset_link_is_still_invalid_token(
    api_client: APIClient, verified_user: User
) -> None:
    """The guard on the split above: the two codes must not drift back together."""
    response = api_client.post(
        reverse("v1:auth:password-reset-confirm"),
        {"uid": "bogus", "token": "bogus", "new_password": "a-brand-new-long-passphrase"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"


def test_a_weak_password_on_change_is_also_weak_password(
    api_client: APIClient, verified_user: User
) -> None:
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:auth:password-change"),
        {"current_password": "correct-horse-battery-staple", "new_password": "1234567890"},
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["code"] == "weak_password"


# ── CSRF on the sign-in endpoints ─────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("v1:auth:login", {"email": "ada@example.com", "password": "correct-horse-battery-staple"}),
        (
            "v1:auth:register",
            {
                "email": "new@example.com",
                "password": "x" * 12,
                "full_name": "N",
                "phone": "+2348000000000",
                "accept_terms": True,
            },
        ),
        ("v1:auth:password-reset", {"email": "ada@example.com"}),
        ("v1:auth:resend-verification", {"email": "ada@example.com"}),
    ],
)
def test_sign_in_endpoints_refuse_a_request_without_a_csrf_token(
    verified_user: User, name: str, payload: dict
) -> None:  # type: ignore[type-arg]
    """Login CSRF: a foreign page must not be able to post these forms."""
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(reverse(name), payload)  # form-encoded, as a hostile page would send
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_login_works_when_the_csrf_token_is_sent(verified_user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    client.get(reverse("v1:auth:csrf"))
    token = client.cookies["kuyash_csrftoken"].value

    response = client.post(
        reverse("v1:auth:login"),
        {"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "ada@example.com"


# ── Social sign-in ────────────────────────────────────────────────────────────


def test_provider_callback_routes_are_mounted() -> None:
    """Without them the redirect endpoint raised NoReverseMatch — a 500."""
    assert reverse("google_callback") == "/accounts/google/login/callback/"
    assert reverse("facebook_callback") == "/accounts/facebook/login/callback/"


@override_settings(
    SOCIALACCOUNT_PROVIDERS=GOOGLE_APP, CSRF_TRUSTED_ORIGINS=["http://localhost:3000"]
)
def test_the_redirect_endpoint_sends_the_browser_to_google() -> None:
    client = APIClient(HTTP_HOST="localhost")
    response = client.post(
        "/_allauth/browser/v1/auth/provider/redirect",
        {
            "provider": "google",
            "process": "login",
            "callback_url": "http://localhost:3000/auth/callback",
        },
    )
    assert response.status_code == 302
    assert response["Location"].startswith("https://accounts.google.com/")
    assert "accounts%2Fgoogle%2Flogin%2Fcallback" in response["Location"]


@override_settings(
    SOCIALACCOUNT_PROVIDERS={"google": {"SCOPE": ["email"]}, "facebook": {"SCOPE": ["email"]}}
)
def test_a_provider_without_credentials_is_not_offered() -> None:
    """The frontend renders a button per listed provider; none may lead nowhere."""
    config = APIClient(HTTP_HOST="localhost").get("/_allauth/browser/v1/config").json()
    assert config["data"]["socialaccount"]["providers"] == []


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE_APP)
def test_a_configured_provider_is_offered() -> None:
    config = APIClient(HTTP_HOST="localhost").get("/_allauth/browser/v1/config").json()
    assert [p["id"] for p in config["data"]["socialaccount"]["providers"]] == ["google"]


# ── Social sign-in failures return the customer to the frontend ───────────────


@override_settings(
    SOCIALACCOUNT_PROVIDERS={"google": {"SCOPE": ["email"]}}, FRONTEND_URL="http://localhost:3000"
)
def test_a_failed_social_sign_in_redirects_instead_of_erroring() -> None:
    """Previously ImproperlyConfigured → 500 for every social failure, including a
    customer simply cancelling on the provider's consent screen."""
    from django.conf import settings

    client = APIClient(HTTP_HOST="localhost")
    response = client.post(
        "/_allauth/browser/v1/auth/provider/redirect",
        {
            "provider": "google",
            "process": "login",
            "callback_url": "http://localhost:3000/auth/callback",
        },
    )

    assert response.status_code == 302
    target = settings.HEADLESS_FRONTEND_URLS["socialaccount_login_error"]
    assert response["Location"].startswith(target)
    assert "error=" in response["Location"]


def test_every_social_error_path_has_a_frontend_url() -> None:
    """Guards the setting itself, independent of which failure triggers it."""
    from django.conf import settings

    assert settings.HEADLESS_FRONTEND_URLS["socialaccount_login_error"].endswith("/auth/callback")
