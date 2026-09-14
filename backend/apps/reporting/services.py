"""Management reports: sales, popular items, peak hours and rider performance.

Everything is bucketed in the branch's own time zone. A "day" is a Lagos day,
not a UTC day — an order at 00:30 on a Saturday belongs to Saturday.

**What counts as a sale.** An order counts when money was taken for it (paid,
or later partly or fully refunded) or when it was a cash order that was
delivered. Unpaid, expired and failed orders are not sales; they are reported
separately as orders that did not complete. Refunds are subtracted in the
period they were issued, so a refund never rewrites last month's figures.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.db.models import Count, F, Q, QuerySet, Sum
from django.utils import timezone

from apps.orders.models import (
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    PaymentMethod,
    PaymentStatus,
)

MAX_DAYS = 366
DEFAULT_DAYS = 7
COUNTED_PAYMENT_STATUSES = (
    PaymentStatus.PAID,
    PaymentStatus.PARTIALLY_REFUNDED,
    PaymentStatus.REFUNDED,
)
INCOMPLETE_STATUSES = (
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
    OrderStatus.FAILED,
)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class PeriodError(ValueError):
    """A report period the caller must correct."""


@dataclass(frozen=True, slots=True)
class Period:
    start: dt.date
    end: dt.date  # inclusive
    tz: dt.tzinfo

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def bounds(self) -> tuple[dt.datetime, dt.datetime]:
        start = dt.datetime.combine(self.start, dt.time.min, tzinfo=self.tz)
        end = dt.datetime.combine(self.end + dt.timedelta(days=1), dt.time.min, tzinfo=self.tz)
        return start, end

    def dates(self) -> list[dt.date]:
        return [self.start + dt.timedelta(days=offset) for offset in range(self.days)]


def period(branch: Any, *, start: str = "", end: str = "") -> Period:
    """Parse ``from``/``to`` (ISO dates, both inclusive). Defaults to the last seven days."""
    tz = branch.tzinfo()
    today = branch.local_now().date()
    try:
        end_date = dt.date.fromisoformat(end) if end else today
        start_date = (
            dt.date.fromisoformat(start)
            if start
            else end_date - dt.timedelta(days=DEFAULT_DAYS - 1)
        )
    except ValueError as exc:
        raise PeriodError("Dates must be written as YYYY-MM-DD.") from exc
    if start_date > end_date:
        raise PeriodError("The start date must be on or before the end date.")
    result = Period(start_date, end_date, tz)
    if result.days > MAX_DAYS:
        raise PeriodError(f"Reports cover at most {MAX_DAYS} days.")
    return result


def _local(moment: dt.datetime, tz: dt.tzinfo) -> dt.datetime:
    return timezone.localtime(moment, timezone=tz)


def counted_orders(branch: Any, window: Period) -> QuerySet[Order]:
    start, end = window.bounds
    return Order.objects.filter(branch=branch, placed_at__gte=start, placed_at__lt=end).filter(
        Q(payment_status__in=COUNTED_PAYMENT_STATUSES)
        | Q(payment_method=PaymentMethod.CASH, status=OrderStatus.DELIVERED)
    )


# ──────────────────────────────────────────────────────────────────────────────
# Sales
# ──────────────────────────────────────────────────────────────────────────────


def sales(branch: Any, window: Period) -> dict[str, Any]:
    from apps.payments.models import Refund, RefundStatus

    orders = counted_orders(branch, window)
    totals = orders.aggregate(
        orders=Count("id"),
        gross=Sum("grand_total"),
        subtotal=Sum("subtotal"),
        discounts=Sum("discount_total"),
        delivery_fees=Sum("delivery_fee"),
        service_charges=Sum("service_charge"),
        vat=Sum("vat_total"),
        tips=Sum("tip"),
    )
    totals = {key: value or 0 for key, value in totals.items()}
    start, end = window.bounds
    refunds = (
        Refund.objects.filter(
            order__branch=branch,
            status=RefundStatus.SUCCESS,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    daily: dict[dt.date, dict[str, int]] = {
        day: {"orders": 0, "gross": 0} for day in window.dates()
    }
    by_payment: dict[str, dict[str, int]] = defaultdict(lambda: {"orders": 0, "gross": 0})
    by_fulfilment: dict[str, dict[str, int]] = defaultdict(lambda: {"orders": 0, "gross": 0})
    prep_minutes: list[float] = []
    for row in orders.values(
        "placed_at", "grand_total", "payment_method", "fulfilment_type", "accepted_at", "ready_at"
    ):
        if row["placed_at"] is None:  # pragma: no cover - the range filter excludes it
            continue
        day = _local(row["placed_at"], window.tz).date()
        for bucket in (
            daily[day],
            by_payment[row["payment_method"]],
            by_fulfilment[row["fulfilment_type"]],
        ):
            bucket["orders"] += 1
            bucket["gross"] += row["grand_total"]
        if row["accepted_at"] and row["ready_at"] and row["ready_at"] >= row["accepted_at"]:
            prep_minutes.append((row["ready_at"] - row["accepted_at"]).total_seconds() / 60)

    incomplete = dict(
        Order.objects.filter(
            branch=branch, placed_at__gte=start, placed_at__lt=end, status__in=INCOMPLETE_STATUSES
        )
        .values_list("status")
        .annotate(total=Count("id"))
    )

    return {
        **totals,
        "refunds": refunds,
        "net": totals["gross"] - refunds,
        "average_order": totals["gross"] // totals["orders"] if totals["orders"] else 0,
        "average_prep_minutes": round(sum(prep_minutes) / len(prep_minutes), 1)
        if prep_minutes
        else None,
        "by_payment_method": dict(by_payment),
        "by_fulfilment": dict(by_fulfilment),
        "incomplete_orders": {status: incomplete.get(status, 0) for status in INCOMPLETE_STATUSES},
        "daily": [{"date": day, **values} for day, values in daily.items()],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Popular items
# ──────────────────────────────────────────────────────────────────────────────


def popular_items(branch: Any, window: Period, *, limit: int = 20) -> list[dict[str, Any]]:
    """Best sellers by quantity, from what was actually sold (the line snapshots)."""
    rows = (
        OrderItem.objects.filter(order__in=counted_orders(branch, window))
        .values("slug_snapshot", "name_snapshot")
        .annotate(
            quantity=Sum("quantity"),
            orders=Count("order", distinct=True),
            revenue=Sum(F("line_subtotal") - F("line_discount")),
        )
        .order_by("-quantity", "-revenue", "name_snapshot")[:limit]
    )
    return [
        {
            "slug": row["slug_snapshot"],
            "name": row["name_snapshot"],
            "quantity": row["quantity"],
            "orders": row["orders"],
            "revenue": row["revenue"],
        }
        for row in rows
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Peak hours
# ──────────────────────────────────────────────────────────────────────────────


def peak_hours(branch: Any, window: Period) -> dict[str, Any]:
    """Orders by local weekday and hour."""
    grid = [[0] * 24 for _ in WEEKDAYS]
    for placed_at in counted_orders(branch, window).values_list("placed_at", flat=True):
        if placed_at is None:  # pragma: no cover - the range filter excludes it
            continue
        local = _local(placed_at, window.tz)
        grid[local.weekday()][local.hour] += 1
    by_hour = [sum(day[hour] for day in grid) for hour in range(24)]
    busiest = max(
        ((weekday, hour, grid[weekday][hour]) for weekday in range(7) for hour in range(24)),
        key=lambda cell: cell[2],
    )
    return {
        "weekdays": list(WEEKDAYS),
        "grid": grid,
        "by_hour": by_hour,
        "busiest": (
            {"weekday": WEEKDAYS[busiest[0]], "hour": busiest[1], "orders": busiest[2]}
            if busiest[2]
            else None
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Riders
# ──────────────────────────────────────────────────────────────────────────────


def rider_performance(branch: Any, window: Period) -> list[dict[str, Any]]:
    """Deliveries completed in the period, per rider.

    Delivery time runs from pick-up (or assignment, if pick-up was not recorded)
    to hand-over. On time means delivered by the estimate the customer was shown.
    """
    from apps.delivery.models import DeliveryAssignment

    start, end = window.bounds
    stats: dict[Any, dict[str, Any]] = {}

    def entry(rider: Any) -> dict[str, Any]:
        return stats.setdefault(
            rider.pk,
            {
                "rider": rider.user.get_full_name(),
                "deliveries": 0,
                "minutes": [],
                "estimated": 0,
                "on_time": 0,
                "failed": 0,
                "cash_collected": 0,
            },
        )

    assignments = DeliveryAssignment.objects.filter(
        order__branch=branch, delivered_at__gte=start, delivered_at__lt=end
    ).select_related("rider__user", "order")
    for assignment in assignments:
        delivered = assignment.delivered_at
        if delivered is None:  # pragma: no cover - the range filter excludes it
            continue
        row = entry(assignment.rider)
        row["deliveries"] += 1
        began = assignment.picked_up_at or assignment.assigned_at
        if began and delivered >= began:
            row["minutes"].append((delivered - began).total_seconds() / 60)
        estimate = assignment.order.estimated_delivery_at
        if estimate:
            row["estimated"] += 1
            row["on_time"] += int(delivered <= estimate)
        row["cash_collected"] += assignment.cash_collected or 0

    failures = OrderStatusEvent.objects.filter(
        order__branch=branch,
        to_status=OrderStatus.FAILED_DELIVERY,
        created_at__gte=start,
        created_at__lt=end,
        order__delivery_assignment__isnull=False,
    ).select_related("order__delivery_assignment__rider__user")
    for event in failures:
        entry(event.order.delivery_assignment.rider)["failed"] += 1

    report = []
    for row in stats.values():
        minutes = row.pop("minutes")
        estimated = row.pop("estimated")
        on_time = row.pop("on_time")
        row["average_delivery_minutes"] = round(sum(minutes) / len(minutes), 1) if minutes else None
        row["on_time_percent"] = round(on_time * 100 / estimated) if estimated else None
        report.append(row)
    return sorted(report, key=lambda row: (-row["deliveries"], row["rider"]))
