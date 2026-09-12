"""Webhook handling.

Rules (docs/PAYMENTS.md §4.3):

* WH-1 verify the signature against the **raw body** before parsing
* WH-2 persist every event, valid or not, before processing
* WH-4 never trust amounts in the payload — re-verify against the provider API
* WH-5 the endpoints are unauthenticated by design; the signature *is* the auth
* WH-7 unknown event types are acknowledged and ignored, never 500'd
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.payments.models import PaymentTransaction, WebhookEvent
from apps.payments.providers.base import parse_money_json
from apps.payments.providers.registry import get_provider

logger = logging.getLogger(__name__)

#: Event types that mean "money moved". Everything else is acknowledged only.
SETTLEMENT_EVENTS = {
    "charge.success",
    "charge.completed",
    "transaction.successful",
}


class WebhookOutcome:
    """What a webhook did, for the view to turn into a status code."""

    def __init__(self, *, accepted: bool, detail: str = "", duplicate: bool = False) -> None:
        self.accepted = accepted
        self.detail = detail
        self.duplicate = duplicate


def handle_webhook(
    *, provider_name: str, raw_body: bytes, headers: Any, remote_addr: str | None = None
) -> WebhookOutcome:
    """Process one inbound webhook."""
    provider = get_provider(provider_name)

    # WH-1: signature first, over the raw bytes.
    valid = provider.verify_webhook(raw_body, headers)
    try:
        payload = parse_money_json(raw_body)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    if not valid:
        # WH-2/WH-6: record the attempt and alert. Repeated failures may be an attack.
        WebhookEvent.objects.create(
            provider=provider_name,
            event_id=f"invalid-{timezone.now().timestamp()}",
            event_type=str(payload.get("event", "")),
            signature_valid=False,
            payload=payload,
            remote_addr=remote_addr,
            processing_error="signature verification failed",
        )
        logger.warning("webhook_signature_invalid", extra={"provider": provider_name})
        return WebhookOutcome(accepted=False, detail="invalid signature")

    event_id, event_type, reference = provider.extract_event(payload)
    if not event_id:
        event_id = f"unidentified-{timezone.now().timestamp()}"

    # WH-2 + idempotency: the unique constraint is the guard.
    try:
        with transaction.atomic():
            event = WebhookEvent.objects.create(
                provider=provider_name,
                event_id=event_id,
                event_type=event_type,
                signature_valid=True,
                payload=payload,
                remote_addr=remote_addr,
            )
    except IntegrityError:
        existing = WebhookEvent.objects.filter(provider=provider_name, event_id=event_id).first()
        if existing is not None and existing.processed_at:
            logger.info("webhook_duplicate_ignored", extra={"event": event_id})
            return WebhookOutcome(accepted=True, detail="already processed", duplicate=True)
        return WebhookOutcome(accepted=True, detail="in progress", duplicate=True)

    # WH-7: acknowledge anything we do not act on.
    if event_type not in SETTLEMENT_EVENTS:
        event.processed_at = timezone.now()
        event.processing_error = ""
        event.save(update_fields=["processed_at", "processing_error", "updated_at"])
        return WebhookOutcome(accepted=True, detail="ignored")

    record = PaymentTransaction.objects.filter(our_reference=reference).first()
    if record is None:
        record = PaymentTransaction.objects.filter(provider_reference=reference).first()
    if record is None:
        event.processed_at = timezone.now()
        event.processing_error = f"no transaction for reference {reference}"
        event.save(update_fields=["processed_at", "processing_error", "updated_at"])
        logger.warning("webhook_unknown_reference", extra={"reference": reference})
        return WebhookOutcome(accepted=True, detail="unknown reference")

    # WH-4: the payload's amount is never trusted. Ask the provider.
    from apps.payments.services.payments import PaymentAmountMismatch, verify_and_settle

    try:
        verify_and_settle(record, source="webhook")
    except PaymentAmountMismatch as exc:
        event.processed_at = timezone.now()
        event.processing_error = str(exc.detail)
        event.save(update_fields=["processed_at", "processing_error", "updated_at"])
        return WebhookOutcome(accepted=True, detail="amount mismatch")
    except Exception as exc:
        event.processing_error = f"{exc.__class__.__name__}: {exc}"
        event.save(update_fields=["processing_error", "updated_at"])
        logger.exception("webhook_processing_failed", extra={"event": event_id})
        return WebhookOutcome(accepted=True, detail="processing error")

    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at", "updated_at"])
    return WebhookOutcome(accepted=True, detail="settled")
