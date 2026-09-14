"""Client IP resolution, and everything that depends on it (SECURITY.md §8)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.adapters import KuyashAccountAdapter
from apps.common import client_ip as client_ip_module
from apps.common.client_ip import AdminIPAllowlistMiddleware, check_proxy_count, client_ip

factory = RequestFactory()


def request_from(remote: str = "203.0.113.9", forwarded: str | None = None, path: str = "/"):  # type: ignore[no-untyped-def]
    extra = {"REMOTE_ADDR": remote}
    if forwarded is not None:
        extra["HTTP_X_FORWARDED_FOR"] = forwarded
    return factory.get(path, **extra)


# ── Resolution ────────────────────────────────────────────────────────────────


def test_with_no_trusted_proxy_the_header_is_ignored(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 0
    assert client_ip(request_from(forwarded="1.2.3.4")) == "203.0.113.9"


def test_one_proxy_takes_the_address_it_appended(settings) -> None:  # type: ignore[no-untyped-def]
    """The client may prepend anything; only the last entry is our proxy's."""
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(request_from(forwarded="6.6.6.6, 198.51.100.7")) == "198.51.100.7"


def test_two_proxies_take_the_second_entry_from_the_right(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 2
    forwarded = "6.6.6.6, 198.51.100.7, 10.0.0.2"
    assert client_ip(request_from(forwarded=forwarded)) == "198.51.100.7"


def test_a_short_chain_falls_back_to_the_socket(settings) -> None:  # type: ignore[no-untyped-def]
    """Fewer entries than proxies: the request skipped a proxy, so trust none of it."""
    settings.TRUSTED_PROXY_COUNT = 2
    assert client_ip(request_from(forwarded="198.51.100.7")) == "203.0.113.9"


def test_no_header_behind_a_proxy_uses_the_socket(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(request_from()) == "203.0.113.9"


@pytest.mark.parametrize("garbage", ["not-an-ip", "", " , ", "1.2.3.4:80"])
def test_garbage_falls_back_to_the_socket(settings, garbage) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(request_from(forwarded=garbage)) == "203.0.113.9"


def test_ipv6_is_normalised(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(request_from(forwarded="2001:DB8::0001")) == "2001:db8::1"


def test_a_missing_socket_address_is_empty(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 0
    assert client_ip(request_from(remote="")) == ""


# ── Throttles cannot be dodged ────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_throttle_ignores_a_rotating_forwarded_header(  # type: ignore[no-untyped-def]
    api_client, throttle_rates, verified_user
) -> None:
    """Regression: DRF keyed anonymous throttles on the raw X-Forwarded-For header.

    A new made-up address per attempt meant the per-IP login limit never fired.
    """
    with throttle_rates(login="3/min"):
        payload = {"email": verified_user.email, "password": "wrong-password-entirely"}
        codes = [
            api_client.post(
                reverse("v1:auth:login"),
                payload,
                format="json",
                HTTP_X_FORWARDED_FOR=f"198.51.100.{index}",
            ).status_code
            for index in range(6)
        ]
    assert 429 in codes


def test_drf_is_told_how_many_proxies_to_trust(settings) -> None:  # type: ignore[no-untyped-def]
    from django.conf import settings as live

    assert live.REST_FRAMEWORK["NUM_PROXIES"] == live.TRUSTED_PROXY_COUNT


def test_allauth_rate_limits_use_the_same_address(settings) -> None:  # type: ignore[no-untyped-def]
    settings.TRUSTED_PROXY_COUNT = 0
    request = request_from(forwarded="6.6.6.6")
    assert KuyashAccountAdapter(request).get_client_ip(request) == "203.0.113.9"
    assert KuyashAccountAdapter(request).get_client_ip(request_from(remote="")) == "0.0.0.0"  # noqa: S104


# ── Admin allowlist ───────────────────────────────────────────────────────────


def _through_allowlist(request):  # type: ignore[no-untyped-def]
    return AdminIPAllowlistMiddleware(lambda _request: "passed")(request)


def test_the_allowlist_is_off_when_empty(settings) -> None:  # type: ignore[no-untyped-def]
    settings.ADMIN_ALLOWED_IPS = []
    assert _through_allowlist(request_from(path="/admin/")) == "passed"


def test_outsiders_get_a_404_for_the_admin(settings) -> None:  # type: ignore[no-untyped-def]
    from django.http import Http404

    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24"]
    settings.ADMIN_URL = "admin/"
    with pytest.raises(Http404):
        _through_allowlist(request_from(path="/admin/login/"))
    with pytest.raises(Http404):
        _through_allowlist(request_from(path="/admin/two-factor/verify/"))


def test_listed_addresses_and_ranges_reach_the_admin(settings) -> None:  # type: ignore[no-untyped-def]
    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24", "203.0.113.9"]
    settings.ADMIN_URL = "admin/"
    assert _through_allowlist(request_from(remote="198.51.100.40", path="/admin/")) == "passed"
    assert _through_allowlist(request_from(path="/admin/")) == "passed"


def test_the_rest_of_the_site_is_unaffected(settings) -> None:  # type: ignore[no-untyped-def]
    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24"]
    assert _through_allowlist(request_from(path="/api/v1/menu/")) == "passed"


def test_the_allowlist_reads_the_trusted_client_address(settings) -> None:  # type: ignore[no-untyped-def]
    """A spoofed header must not open the admin; the proxy's entry must."""
    from django.http import Http404

    settings.ADMIN_ALLOWED_IPS = ["198.51.100.7"]
    settings.ADMIN_URL = "admin/"
    settings.TRUSTED_PROXY_COUNT = 1
    allowed = request_from(remote="10.0.0.1", forwarded="198.51.100.7", path="/admin/")
    assert _through_allowlist(allowed) == "passed"
    spoofed = request_from(remote="10.0.0.1", forwarded="198.51.100.7, 6.6.6.6", path="/admin/")
    with pytest.raises(Http404):
        _through_allowlist(spoofed)


def test_an_unknown_address_is_refused(settings) -> None:  # type: ignore[no-untyped-def]
    from django.http import Http404

    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24"]
    settings.ADMIN_URL = "admin/"
    with pytest.raises(Http404):
        _through_allowlist(request_from(remote="", path="/admin/"))


def test_a_typo_in_the_allowlist_fails_at_startup(settings) -> None:  # type: ignore[no-untyped-def]
    client_ip_module._networks.cache_clear()
    settings.ADMIN_ALLOWED_IPS = ["198.51.100.300"]
    with pytest.raises(ImproperlyConfigured, match="ADMIN_ALLOWED_IPS"):
        AdminIPAllowlistMiddleware(lambda _request: "passed")


@pytest.mark.django_db
def test_the_allowlist_is_installed_before_sessions(client, settings) -> None:  # type: ignore[no-untyped-def]
    from django.conf import settings as live

    order = live.MIDDLEWARE
    assert order.index("apps.common.client_ip.AdminIPAllowlistMiddleware") < order.index(
        "django.contrib.sessions.middleware.SessionMiddleware"
    )
    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24"]
    assert client.get(reverse("admin:login"), REMOTE_ADDR="203.0.113.9").status_code == 404


# ── Deploy check ──────────────────────────────────────────────────────────────


def test_the_deploy_check_warns_behind_a_proxy_with_no_count(settings) -> None:  # type: ignore[no-untyped-def]
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    settings.TRUSTED_PROXY_COUNT = 0
    [warning] = check_proxy_count(None)
    assert warning.id == "kuyash.W021"

    settings.TRUSTED_PROXY_COUNT = 1
    assert check_proxy_count(None) == []

    settings.SECURE_PROXY_SSL_HEADER = None
    settings.TRUSTED_PROXY_COUNT = 0
    assert check_proxy_count(None) == []
