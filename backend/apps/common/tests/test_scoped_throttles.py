"""Scoped write limits actually apply.

Views declared ``throttle_scope`` without ``ScopedRateThrottle`` installed, so
the contact form, catering enquiries, order placement and promo codes were
limited only by the global per-IP rate.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.common.throttling import SCOPED_THROTTLES, WriteScopedRateThrottle

pytestmark = pytest.mark.django_db


def test_every_scoped_view_installs_the_scoped_throttle() -> None:
    from django.urls import get_resolver

    def views(patterns):  # type: ignore[no-untyped-def]
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from views(pattern.url_patterns)
            else:
                cls = getattr(pattern.callback, "cls", None)
                if cls is not None:
                    yield cls

    scoped = {
        cls for cls in views(get_resolver().url_patterns) if getattr(cls, "throttle_scope", None)
    }
    assert scoped, "expected at least one scoped view"
    for cls in scoped:
        assert WriteScopedRateThrottle in cls.throttle_classes, cls.__name__


def test_the_scoped_list_keeps_the_global_limits() -> None:
    from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

    assert AnonRateThrottle in SCOPED_THROTTLES
    assert UserRateThrottle in SCOPED_THROTTLES


def test_the_contact_form_is_limited(api_client, throttle_rates, branch) -> None:  # type: ignore[no-untyped-def]
    payload = {"name": "Ada", "email": "ada@example.com", "message": "Hello there, a question."}
    with throttle_rates(contact="2/hour"):
        codes = [
            api_client.post(reverse("v1:support:contact"), payload, format="json").status_code
            for _ in range(3)
        ]
    assert codes[-1] == 429


def test_reads_do_not_use_up_the_write_allowance(api_client, throttle_rates, verified_user) -> None:  # type: ignore[no-untyped-def]
    """Reading your order history must not stop you placing an order."""
    api_client.force_authenticate(verified_user)
    with throttle_rates(order_create="1/hour"):
        reads = [api_client.get(reverse("v1:orders:create")).status_code for _ in range(3)]
        first = api_client.post(
            reverse("v1:orders:create"), {"payment_method": "card"}, format="json"
        )
        second = api_client.post(
            reverse("v1:orders:create"), {"payment_method": "card"}, format="json"
        )
    assert 429 not in reads
    assert first.status_code != 429
    assert second.status_code == 429
