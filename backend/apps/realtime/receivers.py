"""Order events → socket pushes. `orders` does not import this app (ADR-014)."""

from __future__ import annotations

from typing import Any

from django.dispatch import receiver

from apps.orders.signals import order_paid, order_placed, order_status_changed
from apps.realtime.broadcast import broadcast_after_commit


@receiver(order_placed, dispatch_uid="realtime.push_placed")
@receiver(order_paid, dispatch_uid="realtime.push_paid")
@receiver(order_status_changed, dispatch_uid="realtime.push_status")
def push_order(sender: Any, order: Any, **kwargs: Any) -> None:
    broadcast_after_commit(order)
