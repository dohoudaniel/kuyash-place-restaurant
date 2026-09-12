"""Initialisation, verification, reconciliation and refunds."""

from __future__ import annotations

import datetime as dt

import pytest
import responses
from django.utils import timezone

from apps.common.exceptions import PaymentFailed
from apps.orders.models import OrderStatus, PaymentStatus
from apps.orders.services.state import transition
from apps.payments.models import (
    PaymentTransaction,
    RefundStatus,
    TransactionStatus,
)
from apps.payments.services.payments import (
    PaymentAmountMismatch,
    initialise_payment,
    refund_order,
    verify_and_settle,
    verify_by_reference,
)
from apps.payments.tasks import expire_stale_orders, verify_pending_payments

pytestmark = pytest.mark.django_db

INIT_URL = "https://api.paystack.co/transaction/initialize"
VERIFY_URL = "https://api.paystack.co/transaction/verify/"
REFUND_URL = "https://api.paystack.co/refund"


def mock_init(url: str = "https://checkout.paystack.com/abc123") -> None:
    responses.add(
        responses.POST,
        INIT_URL,
        json={"status": True, "data": {"authorization_url": url, "reference": "ref-1"}},
        status=200,
    )


def mock_verify(reference: str, amount: int, status: str = "success") -> None:
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{reference}",
        json={
            "status": True,
            "data": {
                "status": status,
                "amount": amount,
                "currency": "NGN",
                "channel": "card",
                "gateway_response": "Successful",
                "authorization": {"last4": "4242"},
            },
        },
        status=200,
    )


# ── Initialisation ────────────────────────────────────────────────────────────


@responses.activate
def test_initialise_returns_a_checkout_url(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_init()
    record = initialise_payment(order=order)

    assert record.status == TransactionStatus.PENDING
    assert record.authorization_url.startswith("https://checkout.paystack.com/")
    assert record.amount == order.grand_total


@responses.activate
def test_the_amount_sent_comes_from_the_order_not_the_caller(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """M-6: the charge amount is read from the persisted order."""
    import json

    mock_init()
    initialise_payment(order=order)

    sent = json.loads(responses.calls[0].request.body)
    assert sent["amount"] == order.grand_total
    assert sent["currency"] == "NGN"


@responses.activate
def test_each_attempt_gets_a_fresh_reference(order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Providers reject reused references, so a retry needs a new one."""
    mock_init()
    mock_init()
    first = initialise_payment(order=order)
    second = initialise_payment(order=order)
    assert first.our_reference != second.our_reference


@responses.activate
def test_a_provider_failure_falls_back_to_the_second_provider(  # type: ignore[no-untyped-def]
    order, paystack_keys, flutterwave_keys
) -> None:
    """Outages happen; a second provider is why we integrated two."""
    responses.add(responses.POST, INIT_URL, json={"status": False, "message": "down"}, status=503)
    responses.add(
        responses.POST,
        "https://api.flutterwave.com/v3/payments",
        json={"status": "success", "data": {"link": "https://checkout.flutterwave.com/xyz"}},
        status=200,
    )
    record = initialise_payment(order=order, provider_name="paystack")
    assert record.provider == "flutterwave"
    assert record.status == TransactionStatus.PENDING


def test_cash_orders_cannot_be_initialised(ready_cart, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.services.placement import place_order

    cash = place_order(cart=ready_cart, payment_method="cash")
    with pytest.raises(PaymentFailed, match="settled on delivery"):
        initialise_payment(order=cash)


@responses.activate
def test_an_already_paid_order_cannot_be_charged_again(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)

    transaction.order.refresh_from_db()
    with pytest.raises(PaymentFailed, match="already been paid"):
        initialise_payment(order=transaction.order)


# ── Verification ──────────────────────────────────────────────────────────────


@responses.activate
def test_a_client_cannot_mark_an_order_paid(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The browser's return is a hint to verify, never proof.

    Here the provider says the payment failed, so the order stays unpaid no
    matter who called the endpoint.
    """
    mock_verify(transaction.our_reference, transaction.amount, status="failed")

    verify_by_reference(transaction.our_reference)

    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.FAILED
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT


def test_verifying_an_unknown_reference_returns_nothing(db, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    assert verify_by_reference("KYS-NOSUCH-0000") is None


@responses.activate
def test_verification_is_idempotent(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    verify_and_settle(transaction)  # second call must be a no-op

    assert transaction.order.events.filter(to_status=OrderStatus.PAID).count() == 1


@responses.activate
def test_an_abandoned_payment_is_recorded_as_such(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount, status="abandoned")
    verify_and_settle(transaction)
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.ABANDONED


@responses.activate
def test_a_mismatch_record_survives_the_raise(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The evidence of a suspicious payment must not be rolled back with it."""
    mock_verify(transaction.our_reference, amount=1)
    with pytest.raises(PaymentAmountMismatch):
        verify_and_settle(transaction)

    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.FAILED
    assert transaction.failure_reason == "amount_mismatch"
    assert transaction.amount_verified == 1


# ── Reconciliation ────────────────────────────────────────────────────────────


@responses.activate
def test_reconciliation_settles_a_missed_webhook(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The safety net: money moved but the webhook never arrived."""
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        initialised_at=timezone.now() - dt.timedelta(minutes=10)
    )
    mock_verify(transaction.our_reference, transaction.amount)

    counts = verify_pending_payments()

    assert counts == {"checked": 1, "settled": 1, "failed": 0}
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.SUCCESS
    assert transaction.order.status == OrderStatus.PAID


@responses.activate
def test_reconciliation_skips_recent_transactions(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Give the webhook five minutes before chasing the provider."""
    assert verify_pending_payments()["checked"] == 0


@responses.activate
def test_reconciliation_survives_a_mismatch(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        initialised_at=timezone.now() - dt.timedelta(minutes=10)
    )
    mock_verify(transaction.our_reference, amount=5)

    counts = verify_pending_payments()
    assert counts["failed"] == 1
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT


def test_stale_unpaid_orders_expire(order) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.models import Order

    Order.objects.filter(pk=order.pk).update(placed_at=timezone.now() - dt.timedelta(hours=2))
    assert expire_stale_orders() == 1
    order.refresh_from_db()
    assert order.status == OrderStatus.EXPIRED


def test_recent_unpaid_orders_are_left_alone(order) -> None:  # type: ignore[no-untyped-def]
    assert expire_stale_orders() == 0
    order.refresh_from_db()
    assert order.status == OrderStatus.PENDING_PAYMENT


# ── Refunds ───────────────────────────────────────────────────────────────────


@responses.activate
def test_a_full_refund(transaction, paystack_keys, manager_user) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    responses.add(responses.POST, REFUND_URL, json={"status": True, "data": {"id": 77}}, status=200)

    order = transaction.order
    order.refresh_from_db()
    refund = refund_order(order=order, reason="Kitchen could not fulfil", actor=manager_user)

    assert refund.status == RefundStatus.SUCCESS
    assert refund.amount == order.grand_total
    order.refresh_from_db()
    assert order.payment_status == PaymentStatus.REFUNDED
    assert order.status == OrderStatus.REFUNDED


@responses.activate
def test_a_partial_refund(transaction, paystack_keys, manager_user) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    responses.add(responses.POST, REFUND_URL, json={"status": True, "data": {"id": 78}}, status=200)

    order = transaction.order
    order.refresh_from_db()
    refund_order(order=order, amount_kobo=100_000, reason="Missing side", actor=manager_user)

    order.refresh_from_db()
    assert order.payment_status == PaymentStatus.PARTIALLY_REFUNDED
    assert order.status != OrderStatus.REFUNDED  # still a live order


@responses.activate
def test_refunding_more_than_was_paid_is_refused(transaction, paystack_keys, manager_user) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)

    order = transaction.order
    order.refresh_from_db()
    with pytest.raises(PaymentFailed, match="more than was paid"):
        refund_order(order=order, amount_kobo=order.amount_paid + 1, actor=manager_user)


def test_refunding_an_unpaid_order_is_refused(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PaymentFailed, match="nothing to refund"):
        refund_order(order=order, actor=manager_user)


@responses.activate
def test_a_refund_reverses_the_promo_redemption(  # type: ignore[no-untyped-def]
    ready_cart, promo, paystack_keys, manager_user
) -> None:
    """RF-4: the customer gets their promo use back."""
    from apps.orders.services.placement import place_order
    from apps.promotions.models import PromoRedemption, RedemptionStatus

    ready_cart.promo_code = promo
    ready_cart.save()
    order = place_order(cart=ready_cart, payment_method="card")

    record = PaymentTransaction.objects.create(
        order=order,
        provider="paystack",
        our_reference=f"{order.reference}-x",
        provider_reference=f"{order.reference}-x",
        amount=order.grand_total,
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
    )
    mock_verify(record.our_reference, record.amount)
    verify_and_settle(record)
    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.CONFIRMED

    responses.add(responses.POST, REFUND_URL, json={"status": True, "data": {"id": 9}}, status=200)
    order.refresh_from_db()
    refund_order(order=order, reason="Refunded", actor=manager_user)

    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.REVERSED
    assert promo.times_used == 0


@responses.activate
def test_a_failed_provider_refund_is_recorded_not_silently_applied(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, manager_user
) -> None:
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    responses.add(
        responses.POST, REFUND_URL, json={"status": False, "message": "declined"}, status=400
    )

    order = transaction.order
    order.refresh_from_db()
    refund = refund_order(order=order, actor=manager_user)

    assert refund.status == RefundStatus.FAILED
    order.refresh_from_db()
    assert order.payment_status == PaymentStatus.PAID  # unchanged
    assert order.status != OrderStatus.REFUNDED


def test_a_cash_refund_is_recorded_offline(ready_cart, manager_user, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.services.placement import place_order

    order = place_order(cart=ready_cart, payment_method="cash")
    transition(order, OrderStatus.PREPARING, actor=kitchen_user)
    order.refresh_from_db()
    order.amount_paid = order.grand_total
    order.payment_status = PaymentStatus.PAID
    order.save()

    refund = refund_order(order=order, reason="Never delivered", actor=manager_user)
    assert refund.status == RefundStatus.SUCCESS
    assert refund.transaction is None


def test_a_manual_bank_transfer_settles_the_order(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    from apps.payments.services.payments import record_manual_payment

    record = record_manual_payment(
        order=order, amount_kobo=order.grand_total, actor=manager_user, note="Transfer seen"
    )
    assert record.status == TransactionStatus.SUCCESS
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
