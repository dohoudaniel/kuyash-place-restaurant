"""Order timing."""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.utils import timezone


def estimate(
    *, branch: Any, items: list[Any], fulfilment_type: str, zone_minutes: int | None = None
) -> tuple[dt.datetime, dt.datetime | None]:
    """Estimate when an order will be ready, and delivered.

    Replaces the frontend's hardcoded "30–45 mins" with something derived from
    the dishes ordered, the size of the order and how busy the kitchen is.
    """
    from apps.orders.models import Order, OrderStatus

    prep_times = [
        (getattr(item, "prep_time_minutes", None) or branch.default_prep_minutes) for item in items
    ]
    base = max(prep_times) if prep_times else branch.default_prep_minutes

    volume = sum(getattr(item, "quantity", 1) for item in items)
    base += (volume // 5) * 3  # batching penalty

    active = Order.objects.filter(
        branch=branch, status__in=[OrderStatus.CONFIRMED, OrderStatus.PREPARING]
    ).count()
    load_factor = 1 + min(active / 10, 1.0)  # capped at 2×
    prep_minutes = int(base * load_factor)

    ready_at = timezone.now() + dt.timedelta(minutes=prep_minutes)
    if fulfilment_type != "delivery":
        return ready_at, None
    return ready_at, ready_at + dt.timedelta(minutes=zone_minutes or 40)
