"""One payable, one live checkout link — and never a silent second settlement.

Two tabs, or a customer tapping Pay again while the first page loads, used to
mint two references, both live at the provider. Both could be paid. The second
settlement then found the order already paid and returned silently — and because
``amount_paid`` is set to the order total rather than the sum of what settled,
the second charge could not be refunded through the API at all.
"""

from __future__ import annotations

import datetime as dt
import logging

import pytest
import responses
from django.utils import timezone

from apps.common.exceptions import PaymentFailed
from apps.orders.models import OrderStatus
from apps.orders.services.state import transition
from apps.payments.models import PaymentTransaction, TransactionStatus
from apps.payments.services.payments import initialise_payment, verify_and_settle

pytestmark = pytest.mark.django_db

INIT_URL = "https://api.paystack.co/transaction/initialize"
VERIFY_URL = "https://api.paystack.co/transaction/verify/"


def mock_init(url: str = "https://checkout.paystack.com/abc123") -> None:
    responses.add(
        responses.POST,
        INIT_URL,
        json={"status": True, "data": {"authorization_url": url, "reference": "ref-1"}},
        status=200,
    )


def mock_verify(reference: str, amount: int) -> None:
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{reference}",
        json={
            "status": True,
            "data": {
                "status": "success",
                "amount": amount,
                "currency": "NGN",
                "channel": "card",
                "authorization": {},
            },
        },
        status=200,
    )


# ── One live link ─────────────────────────────────────────────────────────────


@responses.activate
def test_a_second_initialisation_reuses_the_live_checkout_link(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The second tab gets the first tab's link, not a second chargeable one."""
    mock_init()

    first = initialise_payment(order=order)
    second = initialise_payment(order=order)

    assert second.pk == first.pk
    assert second.our_reference == first.our_reference
    assert PaymentTransaction.objects.filter(order=order).count() == 1
    assert len(responses.calls) == 1, "the provider was asked for a second link"


@responses.activate
def test_consent_to_keep_the_card_given_on_a_retry_still_counts(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_init()

    first = initialise_payment(order=order)
    assert first.save_method is False

    second = initialise_payment(order=order, save_method=True)
    assert second.pk == first.pk
    assert second.save_method is True


@responses.activate
def test_a_different_provider_cannot_open_a_second_live_link(  # type: ignore[no-untyped-def]
    order, paystack_keys, flutterwave_keys
) -> None:
    """Honouring this would put two chargeable links on one bill."""
    mock_init()
    initialise_payment(order=order, provider_name="paystack")

    with pytest.raises(PaymentFailed, match="already in progress"):
        initialise_payment(order=order, provider_name="flutterwave")


@responses.activate
def test_a_stale_link_is_replaced_rather_than_reused(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A link nobody used for hours is not worth handing out again."""
    mock_init()
    mock_init("https://checkout.paystack.com/second")

    first = initialise_payment(order=order)
    PaymentTransaction.objects.filter(pk=first.pk).update(
        initialised_at=timezone.now() - dt.timedelta(hours=2)
    )
    second = initialise_payment(order=order)

    assert second.pk != first.pk
    assert second.our_reference != first.our_reference


@responses.activate
def test_a_dead_attempt_does_not_strand_the_customer(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Only a *live* link is reused. A failed one must not block a retry."""
    responses.add(responses.POST, INIT_URL, json={"status": False, "message": "down"}, status=503)
    with pytest.raises(PaymentFailed):
        initialise_payment(order=order, provider_name="paystack")

    responses.reset()
    mock_init()
    record = initialise_payment(order=order, provider_name="paystack")

    assert record.status == TransactionStatus.PENDING
    assert record.authorization_url.startswith("https://checkout.paystack.com/")


# ── Never settle a second charge silently ─────────────────────────────────────


@responses.activate
def test_a_second_settled_charge_is_flagged_not_skipped(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, caplog
) -> None:
    """The money arrived, so it is recorded — and somebody is told."""
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)

    second = PaymentTransaction.objects.create(
        order=transaction.order,
        provider="paystack",
        our_reference=f"{transaction.order.reference}-second",
        provider_reference=f"{transaction.order.reference}-second",
        amount=transaction.amount,
        currency="NGN",
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
    )
    mock_verify(second.our_reference, second.amount)

    with caplog.at_level(logging.CRITICAL):
        settled = verify_and_settle(second)

    assert settled.status == TransactionStatus.SUCCESS
    assert settled.needs_review is True
    assert transaction.our_reference in settled.review_reason
    assert "duplicate_payment_settled" in caplog.text


@responses.activate
def test_money_arriving_for_an_expired_order_is_flagged(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, caplog
) -> None:
    """Expired by the sweep, then paid. Nobody is going to cook this."""
    transition(transaction.order, OrderStatus.EXPIRED, source="system")
    mock_verify(transaction.our_reference, transaction.amount)

    with caplog.at_level(logging.CRITICAL):
        settled = verify_and_settle(transaction)

    assert settled.status == TransactionStatus.SUCCESS
    assert settled.needs_review is True
    assert "payment_settled_against_unpayable_order" in caplog.text

    transaction.order.refresh_from_db()
    assert transaction.order.status == OrderStatus.EXPIRED
