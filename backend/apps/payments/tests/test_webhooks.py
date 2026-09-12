"""Webhook security.

Every case in docs/TESTING.md §4. These are the tests that stand between the
business and giving food away.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
import responses

from apps.orders.models import Order, OrderStatus, PaymentStatus
from apps.payments.models import PaymentTransaction, TransactionStatus, WebhookEvent
from apps.payments.services.webhooks import handle_webhook

pytestmark = pytest.mark.django_db

VERIFY_URL = "https://api.paystack.co/transaction/verify/"


def paystack_payload(reference: str, *, event_id: str = "evt-1") -> dict:
    return {
        "event": "charge.success",
        "data": {"id": event_id, "reference": reference, "status": "success"},
    }


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


def send(payload: dict, secret: str, *, corrupt: bool = False):  # type: ignore[no-untyped-def]
    raw = json.dumps(payload).encode()
    signature = sign(raw, secret)
    if corrupt:
        signature = "deadbeef" + signature[8:]
    return handle_webhook(
        provider_name="paystack",
        raw_body=raw,
        headers={"x-paystack-signature": signature},
        remote_addr="102.89.0.1",
    )


def mock_verify(reference: str, *, amount: int, status: str = "success", currency: str = "NGN"):  # type: ignore[no-untyped-def]
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{reference}",
        json={
            "status": True,
            "data": {
                "status": status,
                "amount": amount,
                "currency": currency,
                "channel": "card",
                "gateway_response": "Successful",
                "authorization": {
                    "authorization_code": "AUTH_abc123",
                    "last4": "4242",
                    "brand": "visa",
                    "exp_month": "12",
                    "exp_year": "2029",
                },
            },
        },
        status=200,
    )


# ── Signature ─────────────────────────────────────────────────────────────────


def test_a_forged_signature_is_rejected(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    outcome = send(paystack_payload(transaction.our_reference), paystack_keys, corrupt=True)

    assert outcome.accepted is False
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT


def test_an_invalid_signature_is_still_recorded(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """WH-2/WH-6: repeated failures may be an attack, so they must be visible."""
    send(paystack_payload(transaction.our_reference), paystack_keys, corrupt=True)
    event = WebhookEvent.objects.get()
    assert event.signature_valid is False
    assert event.remote_addr == "102.89.0.1"


def test_a_missing_signature_header_is_rejected(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    outcome = handle_webhook(
        provider_name="paystack",
        raw_body=json.dumps(paystack_payload(transaction.our_reference)).encode(),
        headers={},
    )
    assert outcome.accepted is False


def test_the_signature_covers_the_raw_body(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Signing a re-serialised dict would let a reformatted body through."""
    payload = paystack_payload(transaction.our_reference)
    raw = json.dumps(payload).encode()
    signature = sign(raw, paystack_keys)

    tampered = json.dumps({**payload, "data": {**payload["data"], "amount": 1}}).encode()
    outcome = handle_webhook(
        provider_name="paystack",
        raw_body=tampered,
        headers={"x-paystack-signature": signature},
    )
    assert outcome.accepted is False


# ── Idempotency ───────────────────────────────────────────────────────────────


@responses.activate
def test_a_replayed_event_settles_once(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Providers retry. A duplicate must not credit the order twice."""
    mock_verify(transaction.our_reference, amount=transaction.amount)
    payload = paystack_payload(transaction.our_reference)

    first = send(payload, paystack_keys)
    second = send(payload, paystack_keys)

    assert first.detail == "settled"
    assert second.duplicate is True
    assert WebhookEvent.objects.filter(signature_valid=True).count() == 1
    assert transaction.order.events.filter(to_status=OrderStatus.PAID).count() == 1


# ── Amount verification ───────────────────────────────────────────────────────


@responses.activate
def test_an_underpayment_never_marks_the_order_paid(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A customer pays ₦100 for a ₦21,800 order."""
    mock_verify(transaction.our_reference, amount=10_000)

    outcome = send(paystack_payload(transaction.our_reference), paystack_keys)

    assert outcome.detail == "amount mismatch"
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.FAILED
    assert transaction.failure_reason == "amount_mismatch"
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT
    assert transaction.order.payment_status != PaymentStatus.PAID


@responses.activate
def test_a_mismatch_is_logged_as_critical(transaction, paystack_keys, caplog) -> None:  # type: ignore[no-untyped-def]
    import logging

    mock_verify(transaction.our_reference, amount=1)
    with caplog.at_level(logging.CRITICAL):
        send(paystack_payload(transaction.our_reference), paystack_keys)
    assert "payment_amount_mismatch" in caplog.text


@responses.activate
def test_a_wrong_currency_is_refused(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, amount=transaction.amount, currency="USD")
    send(paystack_payload(transaction.our_reference), paystack_keys)
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.FAILED


@responses.activate
def test_the_payload_amount_is_never_trusted(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """WH-4. The payload claims success at the right amount; the provider says
    otherwise, and the provider wins."""
    mock_verify(transaction.our_reference, amount=1)
    payload = paystack_payload(transaction.our_reference)
    payload["data"]["amount"] = transaction.amount  # a lie in the payload

    send(payload, paystack_keys)
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.FAILED


# ── Settlement ────────────────────────────────────────────────────────────────


@responses.activate
def test_a_valid_webhook_settles_the_order(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, amount=transaction.amount)

    outcome = send(paystack_payload(transaction.our_reference), paystack_keys)

    assert outcome.detail == "settled"
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.SUCCESS
    assert transaction.amount_verified == transaction.amount
    assert transaction.card_last4 == "4242"
    assert transaction.authorization_code == "AUTH_abc123"

    order = Order.objects.get(pk=transaction.order_id)
    assert order.status == OrderStatus.PAID
    assert order.payment_status == PaymentStatus.PAID
    assert order.amount_paid == order.grand_total


@responses.activate
def test_settlement_clears_the_cart(transaction, paystack_keys, ready_cart) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, amount=transaction.amount)
    assert ready_cart.items.exists()

    send(paystack_payload(transaction.our_reference), paystack_keys)

    ready_cart.refresh_from_db()
    assert not ready_cart.items.exists()


# ── Robustness ────────────────────────────────────────────────────────────────


def test_an_unknown_reference_is_acknowledged(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Acknowledged, not 500'd — otherwise the provider retries forever."""
    outcome = send(paystack_payload("KYS-NOSUCH-000"), paystack_keys)
    assert outcome.accepted is True
    assert outcome.detail == "unknown reference"


def test_an_unhandled_event_type_is_acknowledged(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    payload = paystack_payload(transaction.our_reference)
    payload["event"] = "customer.identification.failed"

    outcome = send(payload, paystack_keys)
    assert outcome.accepted is True
    assert outcome.detail == "ignored"
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING


def test_malformed_json_does_not_crash(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    raw = b"{not json at all"
    outcome = handle_webhook(
        provider_name="paystack",
        raw_body=raw,
        headers={"x-paystack-signature": sign(raw, paystack_keys)},
    )
    assert outcome.accepted is True


@responses.activate
def test_a_provider_outage_during_verification_leaves_it_pending(  # type: ignore[no-untyped-def]
    transaction, paystack_keys
) -> None:
    """Left pending on purpose: reconciliation will pick it up."""
    import requests

    responses.add(
        responses.GET,
        f"{VERIFY_URL}{transaction.our_reference}",
        body=requests.ConnectionError("provider unreachable"),
    )
    send(paystack_payload(transaction.our_reference), paystack_keys)

    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.order.status == OrderStatus.PENDING_PAYMENT


# ── Flutterwave ───────────────────────────────────────────────────────────────


def test_flutterwave_rejects_a_wrong_shared_secret(flutterwave_keys) -> None:  # type: ignore[no-untyped-def]
    outcome = handle_webhook(
        provider_name="flutterwave",
        raw_body=json.dumps({"event": "charge.completed", "data": {"id": 1}}).encode(),
        headers={"verif-hash": "not-the-right-hash"},
    )
    assert outcome.accepted is False


def test_flutterwave_accepts_the_configured_hash(flutterwave_keys, order) -> None:  # type: ignore[no-untyped-def]
    from django.utils import timezone

    record = PaymentTransaction.objects.create(
        order=order,
        provider="flutterwave",
        our_reference="FLW-REF-1",
        provider_reference="FLW-REF-1",
        amount=order.grand_total,
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
    )
    outcome = handle_webhook(
        provider_name="flutterwave",
        raw_body=json.dumps(
            {"event": "charge.completed", "data": {"id": 99, "tx_ref": record.our_reference}}
        ).encode(),
        headers={"verif-hash": "shared-secret-hash"},
    )
    assert outcome.accepted is True
