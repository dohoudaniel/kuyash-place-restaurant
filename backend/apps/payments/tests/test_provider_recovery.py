"""A provider blip must never become a permanent verdict.

``status: false`` is the *envelope* refusing to answer — a bad key, a rate
limit, a reference that has not propagated yet. None of those mean the customer
did not pay. Mapping them to ``failed`` stranded real, paid transactions
forever, because the reconciliation sweep only ever looked at initialised and
pending records: money taken, order never paid, nobody told.

Also here: the row locking that stops the webhook, the customer's return and the
beat sweep from settling the same transaction twice.
"""

from __future__ import annotations

import datetime as dt

import pytest
import responses
from django.utils import timezone

from apps.orders.models import OrderStatus
from apps.payments.models import PaymentTransaction, TransactionStatus
from apps.payments.providers.registry import get_provider
from apps.payments.services.payments import (
    AMOUNT_MISMATCH_REASON,
    _settle,
    verify_and_settle,
)
from apps.payments.tasks import verify_pending_payments

pytestmark = pytest.mark.django_db

VERIFY_URL = "https://api.paystack.co/transaction/verify/"


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


# ── Transient, not terminal ───────────────────────────────────────────────────


@responses.activate
def test_a_provider_refusal_leaves_the_payment_retryable(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """ "Reference not found" often means "not yet", never "they did not pay"."""
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{transaction.our_reference}",
        json={"status": False, "message": "Transaction reference not found"},
        status=400,
    )

    verify_and_settle(transaction)

    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING
    assert "not found" in transaction.failure_reason


@responses.activate
def test_a_non_json_error_page_is_treated_as_an_outage(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A 502 HTML page used to raise ValueError — not a RequestException — so it
    escaped every handler and became an unhandled 500 on the customer's return."""
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{transaction.our_reference}",
        body="<html><body>502 Bad Gateway</body></html>",
        status=502,
        content_type="text/html",
    )

    record = verify_and_settle(transaction)

    assert record.status == TransactionStatus.PENDING
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT


@responses.activate
def test_the_sweep_recovers_a_transaction_stranded_as_failed(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The records the old mapping already wrote still have to be rescued."""
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        status=TransactionStatus.FAILED,
        failure_reason="Transaction reference not found",
        initialised_at=timezone.now() - dt.timedelta(minutes=10),
    )
    mock_verify(transaction.our_reference, transaction.amount)

    counts = verify_pending_payments()

    assert counts["settled"] == 1
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.SUCCESS
    assert transaction.order.status == OrderStatus.PAID


def test_the_sweep_leaves_a_confirmed_mismatch_alone(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A verdict, not an outage: re-asking cannot change it.

    No provider response is registered, so the autouse HTTP guard fails this
    test if the sweep goes anywhere near the network.
    """
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        status=TransactionStatus.FAILED,
        failure_reason=AMOUNT_MISMATCH_REASON,
        initialised_at=timezone.now() - dt.timedelta(minutes=10),
    )

    assert verify_pending_payments()["checked"] == 0


# ── Locking ───────────────────────────────────────────────────────────────────


@responses.activate
def test_settlement_re_reads_the_row_before_touching_it(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """An in-memory copy says whatever it said when it was fetched.

    No provider response is registered here either: the database already says
    this settled, so nothing may call out — and the autouse guard proves it.
    """
    stale = PaymentTransaction.objects.get(pk=transaction.pk)  # another worker's copy
    PaymentTransaction.objects.filter(pk=transaction.pk).update(status=TransactionStatus.SUCCESS)

    settled = verify_and_settle(stale)

    assert settled.status == TransactionStatus.SUCCESS
    assert transaction.order.events.filter(to_status=OrderStatus.PAID).count() == 0


@responses.activate
def test_a_settlement_that_lands_second_does_not_pay_the_order_twice(  # type: ignore[no-untyped-def]
    transaction, paystack_keys
) -> None:
    """The window between asking the provider and writing down the answer.

    Both callers hold a valid "success" from the provider; only one may settle.
    """
    mock_verify(transaction.our_reference, transaction.amount)
    answer = get_provider("paystack").verify(transaction.our_reference)

    # Someone else — the webhook, say — settles while we still hold `answer`.
    verify_and_settle(PaymentTransaction.objects.get(pk=transaction.pk))

    _settle(transaction, answer, source="webhook")

    assert transaction.order.events.filter(to_status=OrderStatus.PAID).count() == 1
