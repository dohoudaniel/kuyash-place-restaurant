"""Social login.

Wires up the two buttons that currently answer
`alert("Google login - Integration needed")`.

The security question these tests exist to settle: can signing in with a social
provider take over somebody else's account?
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from django.test import RequestFactory

from apps.accounts.adapters import KuyashSocialAdapter
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def adapter() -> KuyashSocialAdapter:
    return KuyashSocialAdapter()


@pytest.fixture
def request_():  # type: ignore[no-untyped-def]
    return RequestFactory().get("/_allauth/browser/v1/auth/provider/redirect")


def social_login(
    email: str,
    *,
    verified: bool,
    provider: str = "google",
    name: str = "Ada Obi",
    existing: bool = False,
):  # type: ignore[no-untyped-def]
    """A stand-in for allauth's SocialLogin, carrying only what the adapter reads.

    ``save`` stands in for allauth persisting the user and the social account
    link; the adapter under test only cares that the user row exists afterwards.
    """
    login = SimpleNamespace(
        user=User(email=email, full_name=""),
        account=SimpleNamespace(provider=provider, extra_data={"name": name}),
        email_addresses=[EmailAddress(email=email, verified=verified)],
        is_existing=existing,
    )
    login.save = lambda request, connect=False: login.user.save()  # type: ignore[attr-defined]
    return login


# ── Account takeover ──────────────────────────────────────────────────────────


def test_an_unverified_provider_email_cannot_claim_an_existing_account(  # type: ignore[no-untyped-def]
    adapter, request_, verified_user
) -> None:
    """The attack this guards against: create an account at a provider that does
    not verify addresses, assert the victim's email, and be signed in as them."""
    login = social_login("ada@example.com", verified=False, provider="facebook")

    with pytest.raises(ImmediateHttpResponse) as excinfo:
        adapter.pre_social_login(request_, login)

    response = excinfo.value.response
    assert response.status_code == 409
    assert b"social_email_unverified" in response.content


def test_a_verified_provider_email_may_link(adapter, request_, verified_user) -> None:  # type: ignore[no-untyped-def]
    """Google asserts email_verified, so linking is safe and avoids a confusing
    duplicate-email error for a customer who signed up with a password."""
    login = social_login("ada@example.com", verified=True, provider="google")
    adapter.pre_social_login(request_, login)  # must not raise


def test_a_brand_new_email_is_unaffected(adapter, request_, db) -> None:  # type: ignore[no-untyped-def]
    login = social_login("nobody@example.com", verified=False, provider="facebook")
    adapter.pre_social_login(request_, login)


def test_an_already_connected_account_is_left_alone(adapter, request_, verified_user) -> None:  # type: ignore[no-untyped-def]
    login = social_login("ada@example.com", verified=False, existing=True)
    adapter.pre_social_login(request_, login)


def test_a_login_with_no_email_is_left_alone(adapter, request_, verified_user) -> None:  # type: ignore[no-untyped-def]
    login = social_login("", verified=False)
    login.email_addresses = []
    adapter.pre_social_login(request_, login)


def test_email_matching_is_case_insensitive(adapter, request_, verified_user) -> None:  # type: ignore[no-untyped-def]
    login = social_login("ADA@Example.com", verified=False, provider="facebook")
    with pytest.raises(ImmediateHttpResponse):
        adapter.pre_social_login(request_, login)


# ── Auto signup ───────────────────────────────────────────────────────────────


def test_signup_requires_an_email(adapter, request_, db) -> None:  # type: ignore[no-untyped-def]
    """Without one there is nothing to send an order confirmation to."""
    assert adapter.is_auto_signup_allowed(request_, social_login("", verified=False)) is False
    assert (
        adapter.is_auto_signup_allowed(request_, social_login("new@example.com", verified=True))
        is True
    )


def test_a_social_signup_gets_the_name_and_verified_flag(adapter, request_, db) -> None:  # type: ignore[no-untyped-def]
    """A Google signup should end up with the same profile as a password one."""
    login = social_login("new@example.com", verified=True, name="Chidi Eze")
    login.user.set_unusable_password()

    user = adapter.save_user(request_, login)

    user.refresh_from_db()
    assert user.full_name == "Chidi Eze"
    assert user.is_email_verified is True
    assert hasattr(user, "profile")


def test_an_unverified_social_signup_is_not_marked_verified(adapter, request_, db) -> None:  # type: ignore[no-untyped-def]
    login = social_login("new@example.com", verified=False, provider="facebook")
    login.user.set_unusable_password()

    user = adapter.save_user(request_, login)

    user.refresh_from_db()
    assert user.is_email_verified is False


def test_an_existing_name_is_not_overwritten(adapter, request_, db) -> None:  # type: ignore[no-untyped-def]
    login = social_login("new@example.com", verified=True, name="Provider Name")
    login.user.full_name = "Chosen Name"
    login.user.set_unusable_password()

    user = adapter.save_user(request_, login)
    assert user.full_name == "Chosen Name"


# ── Configuration ─────────────────────────────────────────────────────────────


def test_google_auto_links_but_facebook_does_not() -> None:
    """Google verifies addresses; Facebook's assertion is less reliable."""
    from django.conf import settings

    providers = settings.SOCIALACCOUNT_PROVIDERS
    assert providers["google"]["EMAIL_AUTHENTICATION"] is True
    assert providers["facebook"]["EMAIL_AUTHENTICATION"] is False
    assert providers["facebook"]["VERIFIED_EMAIL"] is False


def test_provider_tokens_are_not_stored() -> None:
    """We never act on the customer's behalf at the provider, so keeping an
    access token would be holding a credential with no purpose."""
    from django.conf import settings

    assert settings.SOCIALACCOUNT_STORE_TOKENS is False


def test_the_provider_endpoints_exist() -> None:
    """The buttons now have somewhere to point."""
    from django.urls import get_resolver

    def walk(resolver, prefix=""):  # type: ignore[no-untyped-def]
        for pattern in resolver.url_patterns:
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern, prefix + str(pattern.pattern))
            else:
                yield prefix + str(pattern.pattern)

    routes = set(walk(get_resolver()))
    assert any("auth/provider/redirect" in route for route in routes)
    assert any("account/providers" in route for route in routes)
