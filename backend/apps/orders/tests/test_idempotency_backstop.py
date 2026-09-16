"""The database refuses a duplicate idempotency key, even without the cache.

The cache is the fast guard; it can be evicted, flushed, or raced by a second
worker. These pin the durable one.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def test_two_orders_cannot_share_an_idempotency_key(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.services.placement import place_order

    order = place_order(cart=ready_cart, payment_method="card", idempotency_key="key-abc")
    assert order.idempotency_key == "key-abc"

    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(
            branch=order.branch,
            user=order.user,
            payment_method="card",
            idempotency_key="key-abc",
            subtotal=0,
            discount_total=0,
            delivery_fee=0,
            service_charge=0,
            vat_total=0,
            tip=0,
            grand_total=0,
            amount_paid=0,
        )


def test_blank_keys_do_not_collide(branch) -> None:  # type: ignore[no-untyped-def]
    """The constraint is partial: older rows carry a blank key and must coexist."""
    for _ in range(2):
        Order.objects.create(
            branch=branch,
            payment_method="cash",
            idempotency_key="",
            subtotal=0,
            discount_total=0,
            delivery_fee=0,
            service_charge=0,
            vat_total=0,
            tip=0,
            grand_total=0,
            amount_paid=0,
        )
    assert Order.objects.filter(idempotency_key="").count() == 2
