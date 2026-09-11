"""User model and session endpoint tests."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def test_user_is_identified_by_email() -> None:
    user = User.objects.create_user(email="Ada@Example.com", password="s3cret-pass-phrase")
    assert user.email == "ada@example.com"  # normalised
    assert user.USERNAME_FIELD == "email"


def test_every_user_gets_a_profile() -> None:
    user = User.objects.create_user(email="ada@example.com", password="s3cret-pass-phrase")
    assert Profile.objects.filter(user=user).exists()


def test_email_must_be_unique() -> None:
    from django.core.exceptions import ValidationError

    User.objects.create_user(email="ada@example.com", password="s3cret-pass-phrase")
    with pytest.raises((ValidationError, Exception)):
        User.objects.create_user(email="ada@example.com", password="another-pass-phrase")


def test_email_is_required() -> None:
    with pytest.raises(ValueError, match="email address is required"):
        User.objects.create_user(email="", password="s3cret-pass-phrase")


def test_superuser_flags() -> None:
    admin = User.objects.create_superuser(email="admin@example.com", password="s3cret-pass-phrase")
    assert admin.is_staff and admin.is_superuser and admin.is_email_verified


def test_superuser_rejects_contradictory_flags() -> None:
    with pytest.raises(ValueError, match="is_staff=True"):
        User.objects.create_superuser(
            email="a@example.com", password="s3cret-pass-phrase", is_staff=False
        )
    with pytest.raises(ValueError, match="is_superuser=True"):
        User.objects.create_superuser(
            email="b@example.com", password="s3cret-pass-phrase", is_superuser=False
        )


def test_invalid_phone_is_rejected() -> None:
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        User.objects.create_user(
            email="ada@example.com", password="s3cret-pass-phrase", phone="not-a-phone"
        )


def test_session_endpoint_is_anonymous_friendly(api_client, db) -> None:  # type: ignore[no-untyped-def]
    """An anonymous visitor gets `{"user": null}`, not a 401."""
    response = api_client.get(reverse("v1:accounts:session"))
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_session_endpoint_returns_the_current_user(api_client, user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=user)
    body = api_client.get(reverse("v1:accounts:session")).json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["full_name"] == "Ada Obi"
    assert body["user"]["groups"] == []


def test_csrf_endpoint_sets_the_cookie(api_client, db) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:accounts:csrf"))
    assert response.status_code == 200
    assert "kuyash_csrftoken" in response.cookies
