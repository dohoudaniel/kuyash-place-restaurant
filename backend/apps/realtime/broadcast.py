"""Push order changes to whoever is watching, after the change is committed."""

from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from apps.realtime import payloads

logger = logging.getLogger(__name__)


def broadcast_order(reference: str) -> None:
    """Send the order to its watchers and the ticket to the kitchen.

    Never raises: a socket that cannot be reached must not fail an order. The
    clients' polling fallback covers a missed push.
    """
    layer = get_channel_layer()
    if layer is None:  # pragma: no cover - CHANNEL_LAYERS is always configured
        return
    try:
        order = payloads.load_order(reference)
        if order is None:
            return
        async_to_sync(layer.group_send)(
            payloads.order_group(reference),
            {"type": "order.updated", "order": payloads.order_payload(order)},
        )
        async_to_sync(layer.group_send)(
            payloads.kitchen_group(order.branch_id),
            {"type": "ticket.updated", "ticket": payloads.ticket_payload(order)},
        )
    except Exception:
        logger.exception("realtime_broadcast_failed", extra={"order": reference})


def broadcast_after_commit(order: Any) -> None:
    """Schedule one push per order per transaction.

    A single change can fire several order signals (paying fires both
    ``order_status_changed`` and ``order_paid``); the watchers need one message
    carrying the final state, not two. Pending callbacks live on the connection
    and are discarded on rollback, so a rolled-back change never suppresses a
    later push.
    """
    reference = order.reference
    connection = transaction.get_connection()
    if connection.in_atomic_block and any(
        getattr(callback, "realtime_reference", None) == reference
        for _savepoints, callback, *_rest in connection.run_on_commit
    ):
        return

    def push() -> None:
        broadcast_order(reference)

    push.realtime_reference = reference  # type: ignore[attr-defined]
    transaction.on_commit(push)
