"""Webhook handling.

Rules (docs/PAYMENTS.md §4.3):

* WH-1 verify the signature against the **raw body** before parsing
* WH-2 persist every event, valid or not, before processing
* WH-4 never trust amounts in the payload — re-verify against the provider API
* WH-5 the endpoints are unauthenticated by design; the signature *is* the auth
* WH-7 unknown event types are acknowledged and ignored, never 500'd
* WH-8 acknowledge immediately and settle in a task

WH-8 is the rule this module used to break. Settling inline meant the provider's
own request waited on *our* outbound call to that same provider: 20 seconds in
the worst case, which is longer than a provider's own timeout, so it retried,
and each retry did it again. Worse, a settlement that failed was marked with a
``processing_error`` but answered 200, so the provider never re-sent it and the
only thing that could recover it was the reconciliation sweep.

Now the request does three things — verify the signature, persist the event,
queue — and the work happens in ``payments.settle_webhook_event``, keyed on the
event row. An event that fails leaves ``processed_at`` unset, which is what both
the sweep and an operator look for.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
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

#: The most payload we are willing to store for one event. A real provider
#: event is a few hundred bytes; the endpoint is unauthenticated, and Django
#: will happily hand us megabytes to write into Postgres on demand.
MAX_STORED_PAYLOAD_BYTES = 16_384


class WebhookOutcome:
    """What a webhook did, for the view to turn into a status code."""

    def __init__(self, *, accepted: bool, detail: str = "", duplicate: bool = False) -> None:
        self.accepted = accepted
        self.detail = detail
        self.duplicate = duplicate


def _capped(payload: dict[str, Any], *, reference: str) -> dict[str, Any]:
    """The payload we are willing to keep, with the reference preserved.

    An oversized event is stored as a stub rather than dropped, and the stub
    keeps the transaction reference in the shape both adapters read it from — so
    settlement still works for an event too big to keep whole.
    """
    size = len(json.dumps(payload, default=str).encode())
    if size <= MAX_STORED_PAYLOAD_BYTES:
        return payload
    logger.warning("webhook_payload_truncated", extra={"bytes": size})
    return {
        "truncated": True,
        "bytes": size,
        "event": str(payload.get("event", ""))[:80],
        "data": {"reference": reference, "tx_ref": reference},
    }


def _record_invalid(
    *, provider_name: str, payload: dict[str, Any], remote_addr: str | None
) -> None:
    """Record a signature failure as one row per address per hour, with a count.

    WH-2/WH-6 still hold — repeated failures may be an attack, so they must be
    visible — but the row that made them visible was itself the vulnerability:
    a unique ``event_id`` per request meant the dedupe guard never fired, and
    the full attacker-controlled payload went into Postgres every time. The
    payload is deliberately **not** kept: it is unauthenticated input, and
    storing it on demand is the denial of service rather than the defence.
    """
    hour = timezone.now().strftime("%Y%m%d%H")
    event_id = f"invalid-{remote_addr or 'unknown'}-{hour}"[:160]
    try:
        with transaction.atomic():
            WebhookEvent.objects.create(
                provider=provider_name,
                event_id=event_id,
                event_type=str(payload.get("event", ""))[:80],
                signature_valid=False,
                payload={},
                remote_addr=remote_addr,
                processing_error="signature verification failed",
            )
    except IntegrityError:
        WebhookEvent.objects.filter(provider=provider_name, event_id=event_id).update(
            attempt_count=F("attempt_count") + 1, updated_at=timezone.now()
        )


def _finish(event: WebhookEvent, *, error: str = "") -> None:
    """Mark an event done. Only ever called when it really is done."""
    event.processed_at = timezone.now()
    event.processing_error = error[:2000]
    event.save(update_fields=["processed_at", "processing_error", "updated_at"])


def handle_webhook(
    *, provider_name: str, raw_body: bytes, headers: Any, remote_addr: str | None = None
) -> WebhookOutcome:
    """Receive one inbound webhook. Fast, and it never calls the provider."""
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
        _record_invalid(provider_name=provider_name, payload=payload, remote_addr=remote_addr)
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
                event_id=event_id[:160],
                event_type=event_type[:80],
                signature_valid=True,
                payload=_capped(payload, reference=reference),
                remote_addr=remote_addr,
            )
    except IntegrityError:
        existing = WebhookEvent.objects.filter(provider=provider_name, event_id=event_id).first()
        if existing is not None:
            WebhookEvent.objects.filter(pk=existing.pk).update(
                attempt_count=F("attempt_count") + 1, updated_at=timezone.now()
            )
            if existing.processed_at:
                logger.info("webhook_duplicate_ignored", extra={"event": event_id})
                return WebhookOutcome(accepted=True, detail="already processed", duplicate=True)
        return WebhookOutcome(accepted=True, detail="in progress", duplicate=True)

    # WH-7: acknowledge anything we do not act on.
    if event_type not in SETTLEMENT_EVENTS:
        _finish(event)
        return WebhookOutcome(accepted=True, detail="ignored")

    # WH-8. The event row is committed by the block above (nothing here runs
    # under ATOMIC_REQUESTS), so the worker cannot pick up an id that does not
    # exist yet. Everything expensive — the outbound verification, settlement,
    # the emails — happens there, not while the provider holds this connection.
    from apps.payments.tasks import settle_webhook_event

    settle_webhook_event.delay(str(event.pk))
    return WebhookOutcome(accepted=True, detail="queued")


def settle_event(event: WebhookEvent) -> str:
    """Do what the webhook asked for. Runs in a task, never in the request.

    Keyed on the event row: a redelivery that got as far as a second task finds
    ``processed_at`` set and does nothing.
    """
    if event.processed_at is not None:
        return "already processed"

    provider = get_provider(event.provider)
    _, _, reference = provider.extract_event(event.payload)

    record = PaymentTransaction.objects.filter(our_reference=reference).first()
    if record is None:
        record = PaymentTransaction.objects.filter(provider_reference=reference).first()
    if record is None:
        _finish(event, error=f"no transaction for reference {reference}")
        logger.warning("webhook_unknown_reference", extra={"reference": reference})
        return "unknown reference"

    # WH-4: the payload's amount is never trusted. Ask the provider.
    from apps.payments.services.payments import PaymentAmountMismatch, verify_and_settle

    try:
        verify_and_settle(record, source="webhook")
    except PaymentAmountMismatch as exc:
        # A verdict, not a failure: the provider answered, and the answer was
        # refused. Nothing more will change by asking again.
        _finish(event, error=str(exc.detail))
        return "amount mismatch"
    except Exception as exc:
        # Deliberately left unprocessed. `processed_at` stays NULL so the event
        # still reads as outstanding to an operator, and the reconciliation
        # sweep remains the safety net for the transaction itself.
        event.processing_error = f"{exc.__class__.__name__}: {exc}"[:2000]
        event.save(update_fields=["processing_error", "updated_at"])
        logger.exception("webhook_processing_failed", extra={"event": event.event_id})
        return "processing error"

    _finish(event)
    return "settled"
