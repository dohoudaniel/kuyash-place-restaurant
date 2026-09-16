"""Who is actually on the other end of a request.

``X-Forwarded-For`` is written by whoever sends the request, so trusting its
leftmost entry lets any caller claim any address — and walk straight past a
per-IP login limit by changing it on every attempt. Only the entries appended
by *our own* proxies can be believed.

``TRUSTED_PROXY_COUNT`` says how many proxies sit in front of Django:

* ``0`` (the default, and local development): the socket address. The header is
  ignored entirely.
* ``1`` (one load balancer or Nginx): the address that proxy saw, which is the
  last entry of ``X-Forwarded-For``.
* ``N``: the Nth entry from the right.

DRF throttles (``NUM_PROXIES``), allauth's rate limits, the admin IP allowlist
and every stored IP go through here, so they all agree. See SECURITY.md §8.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.core.checks import Error, register
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpRequest, HttpResponse


def client_ip(request: HttpRequest) -> str:
    """The client's address as our outermost trusted proxy recorded it."""
    remote = _valid(request.META.get("REMOTE_ADDR", "")) or ""
    trusted = settings.TRUSTED_PROXY_COUNT
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if trusted <= 0 or not forwarded:
        return remote
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if len(hops) < trusted:
        # Fewer entries than proxies: this request did not come through them all.
        return remote
    return _valid(hops[-trusted]) or remote


def _valid(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


# ── Admin IP allowlist ────────────────────────────────────────────────────────


@lru_cache(maxsize=8)
def _networks(
    entries: tuple[str, ...],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    try:
        return tuple(
            ipaddress.ip_network(entry.strip(), strict=False) for entry in entries if entry.strip()
        )
    except ValueError as exc:
        raise ImproperlyConfigured(f"ADMIN_ALLOWED_IPS has an invalid entry: {exc}") from exc


class AdminIPAllowlistMiddleware:
    """Answer 404 for the admin to anyone outside ``ADMIN_ALLOWED_IPS``.

    Off when the list is empty. A 404 rather than a 403, so the admin's location
    is not confirmed to someone scanning for it. Complements, not replaces, a
    network-level allowlist or VPN.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        _networks(tuple(settings.ADMIN_ALLOWED_IPS))  # fail at startup on a typo

    def __call__(self, request: HttpRequest) -> HttpResponse:
        entries = tuple(settings.ADMIN_ALLOWED_IPS)
        if entries and request.path.startswith("/" + settings.ADMIN_URL.lstrip("/")):
            address = client_ip(request)
            allowed = _networks(entries)
            if not address or not any(ipaddress.ip_address(address) in net for net in allowed):
                raise Http404
        return self.get_response(request)


@register("kuyash", deploy=True)
def check_proxy_count(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Behind a TLS-terminating proxy, a count of 0 puts every visitor on one IP.

    An error, not a warning: at 0 every request appears to come from the load
    balancer, so ``order_create: 10/hour`` becomes ten orders per hour for the
    whole restaurant. That is a dead site, not a degraded one.
    """
    if settings.SECURE_PROXY_SSL_HEADER and settings.TRUSTED_PROXY_COUNT <= 0:
        return [
            Error(
                "Django trusts a proxy for HTTPS but TRUSTED_PROXY_COUNT is 0.",
                hint=(
                    "Every request would appear to come from the proxy, so one visitor's "
                    "failed logins throttle everyone. Set TRUSTED_PROXY_COUNT to the number "
                    "of proxies in front of Django (usually 1)."
                ),
                id="kuyash.E021",
            )
        ]
    return []
