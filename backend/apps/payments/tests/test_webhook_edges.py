"""Webhook edge cases and task robustness."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
from unittest import mock

import pytest
from django.utils import timezone

from apps.payments.models import PaymentTransaction, WebhookEvent
from apps.payments.services.webhooks import handle_webhook
from apps.payments.tasks import expire_stale_orders, verify_pending_payments

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


def test_an_unexpected_processing_error_is_recorded_and_acknowledged(  # type: ignore[no-untyped-def]
    transaction, paystack_keys
) -> None:
    """A crash must not make the provider retry forever."""
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
    assert outcome.detail == "processing error"
    event = WebhookEvent.objects.get(event_id="evt-boom")
    assert "RuntimeError" in event.processing_error


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
