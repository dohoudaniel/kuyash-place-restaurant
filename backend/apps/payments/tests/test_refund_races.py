"""Refunds: one at a time, and never with a provider call inside a transaction.

What this replaces held a single database transaction open across a 20-second
provider call, and read the over-refund guard without a lock — so two managers
double-clicking Refund both passed the guard and both refunded.
"""

from __future__ import annotations

import pytest
import responses
from django.db import connection

from apps.common.exceptions import IdempotencyConflict, PaymentFailed
from apps.payments.models import Refund, RefundStatus
from apps.payments.providers.base import RefundResult
from apps.payments.services import payments as payment_services
from apps.payments.services.payments import refund_order, verify_and_settle

pytestmark = pytest.mark.django_db

VERIFY_URL = "https://api.paystack.co/transaction/verify/"
REFUND_URL = "https://api.paystack.co/refund"


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


def settled_order(transaction):  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    order = transaction.order
    order.refresh_from_db()
    return order


@responses.activate
def test_a_double_clicked_refund_only_sends_the_money_back_once(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user
) -> None:
    order = settled_order(transaction)
    responses.add(responses.POST, REFUND_URL, json={"status": True, "data": {"id": 1}}, status=200)

    first = refund_order(order=order, actor=manager_user, idempotency_key="click-1")
    second = refund_order(order=order, actor=manager_user, idempotency_key="click-1")

    assert second.pk == first.pk
    assert Refund.objects.filter(order=order).count() == 1
    assert len([call for call in responses.calls if call.request.url == REFUND_URL]) == 1


@responses.activate
def test_a_refund_still_in_flight_refuses_a_second_click(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user
) -> None:
    """The first click's row is committed before the provider is called; the
    second click finds it and stops rather than refunding alongside it."""
    order = settled_order(transaction)
    Refund.objects.create(
        order=order,
        amount=order.amount_paid,
        status=RefundStatus.PENDING,
        idempotency_key="click-1",
    )

    with pytest.raises(IdempotencyConflict):
        refund_order(order=order, actor=manager_user, idempotency_key="click-1")


@responses.activate
def test_a_refund_in_flight_counts_against_the_total(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user
) -> None:
    """Two managers, two different keys, one bill. The second must not pass."""
    order = settled_order(transaction)
    Refund.objects.create(
        order=order, amount=order.amount_paid, status=RefundStatus.PENDING, idempotency_key="mgr-a"
    )

    with pytest.raises(PaymentFailed, match="more than was paid"):
        refund_order(order=order, actor=manager_user, idempotency_key="mgr-b")


@responses.activate
def test_a_failed_refund_does_not_block_trying_again(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user
) -> None:
    order = settled_order(transaction)
    responses.add(
        responses.POST, REFUND_URL, json={"status": False, "message": "declined"}, status=400
    )
    failed = refund_order(order=order, actor=manager_user, idempotency_key="attempt-1")
    assert failed.status == RefundStatus.FAILED

    responses.reset()
    mock_verify(transaction.our_reference, transaction.amount)
    responses.add(responses.POST, REFUND_URL, json={"status": True, "data": {"id": 2}}, status=200)

    retried = refund_order(order=order, actor=manager_user, idempotency_key="attempt-2")
    assert retried.status == RefundStatus.SUCCESS


@pytest.mark.django_db(transaction=True)
@responses.activate
def test_the_provider_is_called_outside_any_transaction(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user, monkeypatch
) -> None:
    """A 20-second HTTP call with a row lock held is how a connection pool dies.

    Needs a real (committing) test transaction: inside pytest-django's usual
    wrapper every test already looks atomic, so the assertion would be
    meaningless there.
    """
    order = settled_order(transaction)
    seen: dict[str, object] = {}

    class Stub:
        def refund(self, reference: str, amount_kobo: int | None = None) -> RefundResult:
            seen["in_atomic_block"] = connection.in_atomic_block
            seen["row_committed"] = Refund.objects.filter(
                order=order, status=RefundStatus.PENDING
            ).exists()
            return RefundResult(ok=True, provider_reference="rf-1")

    monkeypatch.setattr(payment_services, "get_provider", lambda name: Stub())

    refund = refund_order(order=order, actor=manager_user, reason="Kitchen could not fulfil")

    assert refund.status == RefundStatus.SUCCESS
    assert seen["in_atomic_block"] is False, "the provider was called inside a transaction"
    assert seen["row_committed"] is True, "the refund was not recorded before the call"
