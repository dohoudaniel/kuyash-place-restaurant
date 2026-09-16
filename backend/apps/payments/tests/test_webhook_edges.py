"""Webhook edge cases and task robustness."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
from unittest import mock

import pytest
import responses
from django.utils import timezone

from apps.payments.models import PaymentTransaction, TransactionStatus, WebhookEvent
from apps.payments.services.webhooks import handle_webhook
from apps.payments.tasks import expire_stale_orders, settle_webhook_event, verify_pending_payments

pytestmark = pytest.mark.django_db


def signed(payload: object, secret: str) -> tuple[bytes, dict[str, str]]:
    raw = json.dumps(payload).encode()
    return raw, {"x-paystack-signature": hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()}


def test_a_non_object_payload_is_handled(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A JSON array is valid JSON but not an event."""
    raw, headers = signed([1, 2, 3], paystack_keys)
    outcome = handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)
    assert outcome.accepted is True


def test_an_event_without_an_id_still_gets_recorded(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    raw, headers = signed({"event": "charge.success", "data": {}}, paystack_keys)
    handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)
    event = WebhookEvent.objects.get(signature_valid=True)
    assert event.event_id


def test_a_concurrent_duplicate_is_reported_as_in_progress(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The unique constraint fires while the first delivery is still working."""
    WebhookEvent.objects.create(
        provider="paystack",
        event_id="evt-race",
        event_type="charge.success",
        signature_valid=True,
        payload={},
    )  # created, not yet processed
    raw, headers = signed(
        {
            "event": "charge.success",
            "data": {"id": "evt-race", "reference": transaction.our_reference},
        },
        paystack_keys,
    )
    outcome = handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)
    assert outcome.duplicate is True
    assert outcome.detail == "in progress"


def test_a_failed_settlement_is_recorded_but_never_marked_processed(  # type: ignore[no-untyped-def]
    transaction, paystack_keys
) -> None:
    """A crash must not make the provider retry forever — and must not look done.

    The old behaviour set ``processing_error``, left ``processed_at`` NULL and
    answered 200, so the provider never re-sent it and nothing else ever looked
    at it again. The 200 stays (the event *was* received); what changes is that
    an unfinished event still reads as unfinished.
    """
    raw, headers = signed(
        {
            "event": "charge.success",
            "data": {"id": "evt-boom", "reference": transaction.our_reference},
        },
        paystack_keys,
    )
    with mock.patch(
        "apps.payments.services.payments.verify_and_settle",
        side_effect=RuntimeError("database on fire"),
    ):
        outcome = handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)

    assert outcome.accepted is True
    event = WebhookEvent.objects.get(event_id="evt-boom")
    assert "RuntimeError" in event.processing_error
    assert event.processed_at is None


def test_the_provider_is_not_kept_waiting_while_we_settle(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """WH-8: the request persists the event, queues, and returns.

    Settling inline made the provider's own request wait on our outbound call to
    that same provider — long enough for it to time out and retry, which did it
    all again. No provider response is registered here, so the autouse HTTP
    guard fails this test if any of that work happens in the request.
    """
    raw, headers = signed(
        {
            "event": "charge.success",
            "data": {"id": "evt-queued", "reference": transaction.our_reference},
        },
        paystack_keys,
    )
    with mock.patch("apps.payments.tasks.settle_webhook_event.delay") as queued:
        outcome = handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)

    event = WebhookEvent.objects.get(event_id="evt-queued")
    assert outcome.detail == "queued"
    queued.assert_called_once_with(str(event.pk))
    assert event.processed_at is None
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING


@responses.activate
def test_the_queued_task_settles_the_event(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    responses.add(
        responses.GET,
        f"https://api.paystack.co/transaction/verify/{transaction.our_reference}",
        json={
            "status": True,
            "data": {
                "status": "success",
                "amount": transaction.amount,
                "currency": "NGN",
                "channel": "card",
                "authorization": {},
            },
        },
        status=200,
    )
    raw, headers = signed(
        {
            "event": "charge.success",
            "data": {"id": "evt-task", "reference": transaction.our_reference},
        },
        paystack_keys,
    )
    with mock.patch("apps.payments.tasks.settle_webhook_event.delay"):
        handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)
    event = WebhookEvent.objects.get(event_id="evt-task")

    assert settle_webhook_event(str(event.pk)) == "settled"

    transaction.refresh_from_db()
    event.refresh_from_db()
    assert transaction.status == TransactionStatus.SUCCESS
    assert event.processed_at is not None
    # Keyed on the event: a second run of the same task changes nothing.
    assert settle_webhook_event(str(event.pk)) == "already processed"


def test_a_task_for_an_event_that_vanished_does_not_crash(db) -> None:  # type: ignore[no-untyped-def]
    import uuid

    assert settle_webhook_event(str(uuid.uuid4())) == "missing"


# ── Unauthenticated storage ───────────────────────────────────────────────────


def test_repeated_invalid_signatures_collapse_onto_one_row(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """The dedupe guard never used to fire on these.

    Every invalid delivery got a unique ``event_id`` built from the clock, so
    the unique constraint never matched and anyone could write a row — carrying
    the full attacker-controlled payload — as fast as they could post.
    """
    raw = json.dumps({"event": "charge.success", "data": {"id": "x"}}).encode()
    for _ in range(3):
        handle_webhook(
            provider_name="paystack",
            raw_body=raw,
            headers={"x-paystack-signature": "forged"},
            remote_addr="102.89.0.1",
        )

    event = WebhookEvent.objects.get(signature_valid=False)
    assert event.attempt_count == 3
    assert event.payload == {}, "unauthenticated input is not stored"


def test_invalid_attempts_from_different_addresses_stay_apart(paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Collapsing them all onto one row would hide who is doing it."""
    raw = json.dumps({"event": "charge.success"}).encode()
    for address in ("102.89.0.1", "102.89.0.2"):
        handle_webhook(
            provider_name="paystack",
            raw_body=raw,
            headers={"x-paystack-signature": "forged"},
            remote_addr=address,
        )

    assert WebhookEvent.objects.filter(signature_valid=False).count() == 2


def test_an_oversized_payload_is_stored_as_a_stub(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Signature-verified, but still not worth megabytes of Postgres per event."""
    payload = {
        "event": "charge.success",
        "data": {
            "id": "evt-big",
            "reference": transaction.our_reference,
            "padding": "x" * 40_000,
        },
    }
    raw, headers = signed(payload, paystack_keys)
    with mock.patch("apps.payments.tasks.settle_webhook_event.delay"):
        handle_webhook(provider_name="paystack", raw_body=raw, headers=headers)

    event = WebhookEvent.objects.get(event_id="evt-big")
    assert event.payload["truncated"] is True
    assert "padding" not in json.dumps(event.payload)
    # The reference survives the truncation, so the task can still settle it.
    assert event.payload["data"]["reference"] == transaction.our_reference


def test_reconciliation_survives_an_unexpected_error(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """One bad record must not stop the sweep."""
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        initialised_at=timezone.now() - dt.timedelta(minutes=10)
    )
    with mock.patch(
        "apps.payments.services.payments.verify_and_settle",
        side_effect=RuntimeError("provider returned nonsense"),
    ):
        counts = verify_pending_payments()
    assert counts == {"checked": 1, "settled": 1 - 1, "failed": 1}


def test_reconciliation_ignores_transactions_older_than_a_day(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Beyond 24 hours it is a reconciliation problem for a human, not a sweep."""
    PaymentTransaction.objects.filter(pk=transaction.pk).update(
        initialised_at=timezone.now() - dt.timedelta(days=3)
    )
    assert verify_pending_payments()["checked"] == 0


def test_expiry_survives_an_unexpected_error(order) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.models import Order

    Order.objects.filter(pk=order.pk).update(placed_at=timezone.now() - dt.timedelta(hours=2))
    with mock.patch("apps.orders.services.state.transition", side_effect=RuntimeError("locked")):
        assert expire_stale_orders() == 0
    order.refresh_from_db()
    assert order.status != "expired"
