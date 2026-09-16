"""Settings and surfaces the backend audit flagged: compression, sessions, the
second auth surface, the public settings allowlist, and two deploy checks that
turn a launch-day landmine into a build failure.
"""

from __future__ import annotations

import pytest
from django.conf import settings as django_settings
from django.core.checks import Error
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.checks import check_cache_is_shared, check_proxy_count_behind_a_proxy
from apps.core.models import LegalPage, SiteSettings

pytestmark = pytest.mark.django_db

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
REDIS = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
    }
}


def ids(issues: list) -> list[str]:  # type: ignore[type-arg]
    return [issue.id for issue in issues]


# ── Compression ───────────────────────────────────────────────────────────────


def test_gzip_runs_after_everything_that_writes_a_body() -> None:
    """The response phase runs bottom-to-top, so compressing last means being
    listed early."""
    order = django_settings.MIDDLEWARE.index
    assert order("django.middleware.gzip.GZipMiddleware") < order(
        "django.contrib.sessions.middleware.SessionMiddleware"
    )


def test_a_large_public_response_is_compressed(api_client, db) -> None:  # type: ignore[no-untyped-def]
    LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms",
        body="These are the terms of service. " * 100,
        published=True,
    )
    response = api_client.get(
        reverse("v1:core:legal-detail", kwargs={"slug": "terms"}),
        HTTP_ACCEPT_ENCODING="gzip",
    )
    assert response.status_code == 200
    assert response["Content-Encoding"] == "gzip"


# ── Sessions ──────────────────────────────────────────────────────────────────


def test_sessions_are_cached_and_not_rewritten_on_every_request() -> None:
    """django_session was the hottest write table in the system: one UPDATE per
    request per signed-in customer."""
    assert django_settings.SESSION_ENGINE == "django.contrib.sessions.backends.cached_db"
    assert django_settings.SESSION_SAVE_EVERY_REQUEST is False


def test_a_session_still_carries_across_requests(verified_user) -> None:  # type: ignore[no-untyped-def]
    """The write was dropped, not the session."""
    client = APIClient()
    client.force_login(verified_user)
    for _ in range(2):
        body = client.get(reverse("v1:auth:session")).json()
        assert body["user"]["email"] == verified_user.email


# ── The public settings endpoint ──────────────────────────────────────────────


def test_the_internal_mailboxes_are_not_published(api_client, db) -> None:  # type: ignore[no-untyped-def]
    """`exclude` served the addresses internal alerts go to, unauthenticated."""
    row = SiteSettings.load()
    row.support_email = "support@kuyashplace.com"
    row.orders_email = "orders@kuyashplace.com"
    row.save()

    body = api_client.get(reverse("v1:core:settings")).json()

    assert "support_email" not in body
    assert "orders_email" not in body
    # And the allowlist is exactly what it says, so a field added to the model
    # tomorrow is not published by omission.
    assert set(body) == {
        "site_name",
        "tagline",
        "meta_description",
        "instagram_url",
        "facebook_url",
        "twitter_url",
        "tiktok_url",
        "established_year",
        "stat_customers",
        "stat_dishes",
        "stat_years",
        "stat_rating",
    }


# ── The second auth surface ───────────────────────────────────────────────────


def test_only_the_browser_client_is_mounted() -> None:
    assert django_settings.HEADLESS_CLIENTS == ["browser"]


def test_the_app_client_routes_are_gone() -> None:
    """They issued session tokens for a client the frontend never used."""
    client = APIClient(HTTP_HOST="localhost")
    assert client.get("/_allauth/app/v1/config").status_code == 404


@pytest.mark.parametrize("path", ["account/email", "account/phone"])
def test_a_customer_cannot_manage_identities_through_the_headless_surface(
    verified_user, path: str
) -> None:  # type: ignore[no-untyped-def]
    """`GET /_allauth/browser/v1/account/email` returned 200 for a signed-in
    customer and let them add an address and promote it to primary — with none
    of the re-verification the account serializer's read-only `email` exists to
    force."""
    client = APIClient(HTTP_HOST="localhost")
    client.force_login(verified_user)
    response = client.get(f"/_allauth/browser/v1/{path}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_the_rest_of_the_browser_surface_still_works() -> None:
    """Social sign-in goes through this client; breaking it breaks both buttons."""
    client = APIClient(HTTP_HOST="localhost")
    assert client.get("/_allauth/browser/v1/config").status_code == 200


# ── Deploy checks ─────────────────────────────────────────────────────────────


@override_settings(
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"), TRUSTED_PROXY_COUNT=0
)
def test_a_proxy_with_no_proxy_count_blocks_deployment() -> None:
    """Behind a load balancer this makes `order_create: 10/hour` mean ten orders
    an hour for the whole restaurant."""
    issues = check_proxy_count_behind_a_proxy(None)
    assert ids(issues) == ["kuyash.E021"]
    assert all(isinstance(issue, Error) for issue in issues)


@override_settings(
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"), TRUSTED_PROXY_COUNT=1
)
def test_a_configured_proxy_count_passes() -> None:
    assert check_proxy_count_behind_a_proxy(None) == []


@override_settings(SECURE_PROXY_SSL_HEADER=None, TRUSTED_PROXY_COUNT=0)
def test_no_proxy_means_nothing_to_complain_about() -> None:
    assert check_proxy_count_behind_a_proxy(None) == []


@override_settings(DEBUG=False, CACHES=LOCMEM)
def test_a_per_process_cache_blocks_deployment() -> None:
    issues = check_cache_is_shared(None)
    assert ids(issues) == ["kuyash.E022"]
    assert all(isinstance(issue, Error) for issue in issues)


@override_settings(DEBUG=False, CACHES=REDIS)
def test_a_shared_cache_passes() -> None:
    assert check_cache_is_shared(None) == []


@override_settings(DEBUG=True, CACHES=LOCMEM)
def test_local_development_is_left_alone() -> None:
    assert check_cache_is_shared(None) == []


# ── Settings that were lying ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    ["DEFAULT_CURRENCY", "DEFAULT_VAT_RATE_BPS", "PAYSTACK_PUBLIC_KEY", "FLUTTERWAVE_PUBLIC_KEY"],
)
def test_settings_nothing_reads_are_gone(name: str) -> None:
    """Changing the VAT rate in the obvious place did nothing at all, silently."""
    assert not hasattr(django_settings, name)


def test_the_vat_rate_has_exactly_one_home() -> None:
    from apps.common.money import DEFAULT_CURRENCY, DEFAULT_VAT_RATE_BPS

    assert (DEFAULT_CURRENCY, DEFAULT_VAT_RATE_BPS) == ("NGN", 750)
