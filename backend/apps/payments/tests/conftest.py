"""Payment test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def order(ready_cart):  # type: ignore[no-untyped-def]
    """A placed, unpaid card order worth ₦21,800."""
    from apps.orders.services.placement import place_order

    return place_order(cart=ready_cart, payment_method="card")


@pytest.fixture
def paystack_keys(settings):  # type: ignore[no-untyped-def]
    settings.PAYSTACK_SECRET_KEY = "sk_test_not_a_real_key"
    settings.DEBUG = False  # so the dummy provider cannot be substituted
    return settings.PAYSTACK_SECRET_KEY


@pytest.fixture
def flutterwave_keys(settings):  # type: ignore[no-untyped-def]
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-not-real"
    settings.FLUTTERWAVE_WEBHOOK_SECRET_HASH = "shared-secret-hash"
    settings.DEBUG = False
    return settings.FLUTTERWAVE_SECRET_KEY


@pytest.fixture
def transaction(order, paystack_keys):  # type: ignore[no-untyped-def]
    """A pending Paystack transaction for the order."""
    from django.utils import timezone

    from apps.payments.models import PaymentTransaction, TransactionStatus

    return PaymentTransaction.objects.create(
        order=order,
        provider="paystack",
        our_reference=f"{order.reference}-abc123",
        provider_reference=f"{order.reference}-abc123",
        amount=order.grand_total,
        currency="NGN",
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
    )
