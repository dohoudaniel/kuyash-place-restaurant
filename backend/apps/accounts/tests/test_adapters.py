"""allauth adapter tests.

The signup form collects a full name, phone and a newsletter opt-in. Without the
adapter those fields are silently dropped and every customer is nameless.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.accounts.adapters import KuyashAccountAdapter
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def fake_form(**cleaned: object) -> SimpleNamespace:
    base = {"email": "ada@example.com", "password1": "correct-horse-battery-staple"}
    return SimpleNamespace(cleaned_data={**base, **cleaned})


@pytest.fixture
def adapter() -> KuyashAccountAdapter:
    return KuyashAccountAdapter()


@pytest.fixture
def request_() -> object:
    return RequestFactory().post("/signup/")


def test_signup_captures_full_name_and_phone(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    user = adapter.save_user(
        request_, User(), fake_form(full_name="Ada Obi", phone="+2348012345678")
    )
    user.refresh_from_db()
    assert user.full_name == "Ada Obi"
    assert user.phone == "+2348012345678"


def test_signup_without_optional_fields_still_works(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    """Social sign-in may supply neither a name nor a phone."""
    user = adapter.save_user(request_, User(), fake_form())
    assert user.pk is not None
    assert user.full_name == ""
    assert user.phone == ""


def test_marketing_opt_in_is_recorded(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    """Consent is explicit and stored, because NDPR requires it to be withdrawable."""
    user = adapter.save_user(request_, User(), fake_form(marketing_opt_in=True))
    assert user.profile.marketing_opt_in is True


def test_marketing_opt_out_is_the_default(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    user = adapter.save_user(request_, User(), fake_form(marketing_opt_in=False))
    assert user.profile.marketing_opt_in is False


def test_password_is_hashed_not_stored(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    user = adapter.save_user(request_, User(), fake_form())
    assert user.password != "correct-horse-battery-staple"
    assert user.check_password("correct-horse-battery-staple")


def test_confirming_email_sets_our_verification_flag(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    """allauth tracks verification on EmailAddress; we mirror it onto the user."""
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(email="ada@example.com", password="s3cret-pass-phrase")
    assert user.is_email_verified is False

    email_address = EmailAddress.objects.create(user=user, email=user.email, primary=True)
    adapter.confirm_email(request_, email_address)

    user.refresh_from_db()
    assert user.is_email_verified is True


def test_confirming_an_already_verified_email_is_a_no_op(adapter, request_) -> None:  # type: ignore[no-untyped-def]
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(email="ada@example.com", password="s3cret-pass-phrase")
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    email_address = EmailAddress.objects.create(user=user, email=user.email, primary=True)
    adapter.confirm_email(request_, email_address)

    user.refresh_from_db()
    assert user.is_email_verified is True
