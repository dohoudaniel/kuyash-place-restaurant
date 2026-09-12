"""Rate limiting on the auth endpoints (SECURITY.md AS-4)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

WRONG = "wrong-password-entirely"


def test_login_is_throttled_per_ip(api_client, throttle_rates, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    with throttle_rates(login="3/min"):
        payload = {"email": "ada@example.com", "password": WRONG}
        codes = [
            api_client.post(reverse("v1:auth:login"), payload, format="json").status_code
            for _ in range(5)
        ]
    assert codes[:3] == [401, 401, 401]
    assert 429 in codes


def test_login_is_throttled_per_email_across_addresses(  # type: ignore[no-untyped-def]
    api_client, throttle_rates, verified_user: User
) -> None:
    """Per-IP alone lets a botnet spread one attack over many addresses."""
    with throttle_rates(login=None, login_email="3/hour"):
        payload = {"email": "ada@example.com", "password": WRONG}
        codes = [
            api_client.post(
                reverse("v1:auth:login"),
                payload,
                format="json",
                REMOTE_ADDR=f"203.0.113.{index}",  # a different source each time
            ).status_code
            for index in range(5)
        ]
    assert 429 in codes


def test_throttled_responses_carry_retry_after(  # type: ignore[no-untyped-def]
    api_client, throttle_rates, verified_user: User
) -> None:
    with throttle_rates(login="1/min"):
        payload = {"email": "ada@example.com", "password": WRONG}
        api_client.post(reverse("v1:auth:login"), payload, format="json")
        response = api_client.post(reverse("v1:auth:login"), payload, format="json")

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert "Retry-After" in response
    assert response.json()["retry_after"] >= 0


def test_registration_is_throttled(api_client, throttle_rates) -> None:  # type: ignore[no-untyped-def]
    with throttle_rates(register="2/hour"):
        codes = [
            api_client.post(
                reverse("v1:auth:register"),
                {
                    "email": f"user{index}@example.com",
                    "password": "correct-horse-battery-staple",
                    "full_name": "Test User",
                    "phone": "+2348012345678",
                    "accept_terms": True,
                },
                format="json",
            ).status_code
            for index in range(4)
        ]
    assert codes[:2] == [201, 201]
    assert 429 in codes


def test_password_reset_is_throttled_per_email(  # type: ignore[no-untyped-def]
    api_client, throttle_rates, verified_user: User
) -> None:
    """Stops a reset-email flood aimed at one inbox from many addresses."""
    with throttle_rates(password_reset=None, password_reset_email="2/hour"):
        codes = [
            api_client.post(
                reverse("v1:auth:password-reset"),
                {"email": "ada@example.com"},
                format="json",
                REMOTE_ADDR=f"203.0.113.{index}",
            ).status_code
            for index in range(4)
        ]
    assert 429 in codes


def test_throttling_is_off_by_default_in_tests(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    """Guard the guard: if rates leak into the suite, unrelated tests get 429s."""
    payload = {"email": "ada@example.com", "password": WRONG}
    codes = [
        api_client.post(reverse("v1:auth:login"), payload, format="json").status_code
        for _ in range(8)
    ]
    assert 429 not in codes
