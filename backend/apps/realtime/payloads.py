"""Socket payloads — the same shapes as the REST responses, JSON-safe."""

from __future__ import annotations

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from apps.orders.models import Order

#: What the kitchen queue shows, as `GET /kds/orders/` does by default.
KDS_STATUSES = ("paid", "confirmed", "preparing", "ready", "out_for_delivery")


def order_group(reference: str) -> str:
    return f"order.{reference}"


def kitchen_group(branch_id: Any) -> str:
    return f"kds.{branch_id}"


def jsonable(value: Any) -> Any:
    """Round-trip through JSON so a Redis channel layer can carry it."""
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def load_order(reference: str) -> Order | None:
    return (
        Order.objects.prefetch_related("items__modifiers", "items__reviews", "events")
        .select_related("branch")
        .filter(reference=reference)
        .first()
    )


def order_payload(order: Order) -> dict[str, Any]:
    from apps.orders.serializers import serialise_order

    return jsonable(serialise_order(order))


def ticket_payload(order: Order) -> dict[str, Any]:
    from apps.orders.serializers import kds_ticket

    return jsonable(kds_ticket(order))


def queue_payload(branch: Any) -> list[dict[str, Any]]:
    orders = (
        Order.objects.filter(branch=branch, status__in=KDS_STATUSES)
        .prefetch_related("items__modifiers")
        .order_by("placed_at", "created_at")
    )
    return [ticket_payload(order) for order in orders]
