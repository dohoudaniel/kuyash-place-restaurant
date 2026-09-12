"""The order state machine.

``Order.status`` is mutated **only** through :func:`transition`. Nothing else
in the codebase assigns to it.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import IllegalTransition
from apps.common.permissions import GROUP_KITCHEN, GROUP_MANAGERS, GROUP_RIDERS, in_group
from apps.orders.models import EventSource, Order, OrderStatus, OrderStatusEvent
from apps.orders.signals import order_paid, order_status_changed

logger = logging.getLogger(__name__)

#: Legal transitions. Anything absent is rejected.
TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING_PAYMENT: {
        OrderStatus.PAID,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    },
    OrderStatus.PAID: {
        OrderStatus.CONFIRMED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.PREPARING,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED, OrderStatus.REFUNDED},
    OrderStatus.READY: {
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.FAILED_DELIVERY},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.FAILED_DELIVERY: {
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.REJECTED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: {OrderStatus.REFUNDED},
    OrderStatus.EXPIRED: set(),
    OrderStatus.REFUNDED: set(),
    OrderStatus.FAILED: set(),
}

#: Timestamp stamped when a status is reached.
_TIMESTAMP_FIELD: dict[str, str] = {
    OrderStatus.CONFIRMED: "accepted_at",
    OrderStatus.READY: "ready_at",
    OrderStatus.OUT_FOR_DELIVERY: "dispatched_at",
    OrderStatus.DELIVERED: "delivered_at",
    OrderStatus.CANCELLED: "cancelled_at",
}

#: Who may drive each transition. Managers and superusers may do anything staff can.
_KITCHEN = {OrderStatus.CONFIRMED, OrderStatus.REJECTED, OrderStatus.PREPARING, OrderStatus.READY}
_RIDER = {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED, OrderStatus.FAILED_DELIVERY}
_MANAGER_ONLY = {OrderStatus.REFUNDED}


def can_transition(actor: Any, to_status: str) -> bool:
    """Whether ``actor`` may move an order to ``to_status``."""
    if actor is None:
        return True  # system-driven: webhooks, beat tasks
    if getattr(actor, "is_superuser", False) or in_group(actor, GROUP_MANAGERS):
        return True
    if to_status in _MANAGER_ONLY:
        return False
    if to_status in _KITCHEN:
        return in_group(actor, GROUP_KITCHEN)
    if to_status in _RIDER:
        return in_group(actor, GROUP_KITCHEN, GROUP_RIDERS)
    return False


def _role_of(actor: Any) -> str:
    if actor is None:
        return "system"
    if getattr(actor, "is_superuser", False):
        return "admin"
    names = sorted(group.name for group in actor.groups.all())
    return ",".join(names) or "customer"


@transaction.atomic
def transition(
    order: Order,
    to_status: str,
    *,
    actor: Any = None,
    source: str = EventSource.SYSTEM,
    note: str = "",
) -> Order:
    """Move an order to a new status, or refuse.

    ``select_for_update`` is what stops two staff members double-advancing the
    same ticket during a rush; on SQLite it degrades to the surrounding
    transaction, which is sufficient for local development (ADR-015).
    """
    from django.conf import settings

    queryset = Order.objects.filter(pk=order.pk)
    if settings.USING_POSTGRES:  # pragma: no cover - exercised in Postgres CI
        # SQLite has no row locking; the surrounding transaction is the best it
        # offers, which is sufficient for local development (ADR-015).
        queryset = queryset.select_for_update()
    locked = queryset.get()

    allowed = TRANSITIONS.get(locked.status, set())
    if to_status not in allowed:
        raise IllegalTransition(
            f"An order that is {locked.get_status_display().lower()} cannot become "
            f"{OrderStatus(to_status).label.lower()}."
        )
    if not can_transition(actor, to_status):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("You are not allowed to make that change.")

    previous = locked.status
    locked.status = to_status
    fields = ["status", "updated_at"]

    stamp = _TIMESTAMP_FIELD.get(to_status)
    if stamp and getattr(locked, stamp) is None:
        setattr(locked, stamp, timezone.now())
        fields.append(stamp)

    if to_status == OrderStatus.CANCELLED and note:
        locked.cancellation_reason = note
        fields.append("cancellation_reason")

    locked.save(update_fields=fields)

    OrderStatusEvent.objects.create(
        order=locked,
        from_status=previous,
        to_status=to_status,
        actor=actor if actor is not None and getattr(actor, "pk", None) else None,
        actor_role=_role_of(actor),
        source=source,
        note=note,
    )

    logger.info(
        "order_status_changed",
        extra={"order": locked.reference, "from": previous, "to": to_status},
    )
    order_status_changed.send(sender=Order, order=locked, from_status=previous, to_status=to_status)
    if to_status == OrderStatus.PAID:
        order_paid.send(sender=Order, order=locked)

    order.status = to_status
    return locked


def timeline(order: Order) -> list[dict[str, Any]]:
    """The customer-facing progress list.

    Built from the append-only event log, and shaped to match the timeline
    component the frontend already renders against mock data.
    """
    happy_path = [
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ]
    if order.fulfilment_type == "delivery":
        happy_path.append(OrderStatus.OUT_FOR_DELIVERY)
    happy_path.append(OrderStatus.DELIVERED)

    reached = {event.to_status: event.created_at for event in order.events.all()}
    steps = [
        {
            "status": status,
            "label": OrderStatus(status).label,
            "at": reached[status].isoformat() if status in reached else None,
            "reached": status in reached,
        }
        for status in happy_path
    ]

    terminal = {
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.REFUNDED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
        OrderStatus.FAILED_DELIVERY,
    }
    if order.status in terminal:
        reached_at = reached.get(order.status)
        steps.append(
            {
                "status": order.status,
                "label": OrderStatus(order.status).label,
                "at": reached_at.isoformat() if reached_at else None,
                "reached": True,
            }
        )
    return steps
