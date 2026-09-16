"""Management reports: sales, popular items, peak hours and rider performance.

Everything is bucketed in the branch's own time zone. A "day" is a Lagos day,
not a UTC day — an order at 00:30 on a Saturday belongs to Saturday.

**What counts as a sale.** An order counts when money was taken for it (paid,
or later partly or fully refunded) or when it was a cash order that was
delivered. Unpaid, expired and failed orders are not sales; they are reported
separately as orders that did not complete. Refunds are subtracted in the
period they were issued, so a refund never rewrites last month's figures.

**Bucketing happens in the database.** Every figure here used to be computed by
pulling the whole result set into Python and adding it up row by row — up to
366 days of orders, in a synchronous request. The local day and hour are now
``TruncDate``/``Extract`` with the branch's ``tzinfo``, so the answer is the same
and the work is the database's.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from django.db.models import Count, DurationField, F, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce, ExtractHour, ExtractIsoWeekDay, TruncDate

from apps.core.cache import SALES_REPORT_KEY, cached
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

#: The kitchen display polls its summary every ten seconds per screen, and that
#: summary asks for today's sales — the same figures, recomputed for every poll
#: of every screen. Half a minute of staleness on a running revenue total is
#: invisible to a manager and turns a per-poll aggregate into a cache read.
#: Managers' own reports ride along; pass ``refresh=True`` to bypass.
SALES_CACHE_SECONDS = 30


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


def counted_orders(branch: Any, window: Period) -> QuerySet[Order]:
    start, end = window.bounds
    return Order.objects.filter(branch=branch, placed_at__gte=start, placed_at__lt=end).filter(
        Q(payment_status__in=COUNTED_PAYMENT_STATUSES)
        | Q(payment_method=PaymentMethod.CASH, status=OrderStatus.DELIVERED)
    )


def _average_minutes(total: Any, count: int) -> float | None:
    """The mean of a summed duration, in minutes.

    Postgres sums intervals and hands back a ``timedelta``; SQLite stores
    durations as microseconds and hands back a number. Both are handled here so
    a report reads the same on a laptop as in production.
    """
    if not count or total is None:
        return None
    seconds = total.total_seconds() if isinstance(total, dt.timedelta) else float(total) / 1_000_000
    return round(seconds / count / 60, 1)


# ──────────────────────────────────────────────────────────────────────────────
# Sales
# ──────────────────────────────────────────────────────────────────────────────


def sales(branch: Any, window: Period, *, refresh: bool = False) -> dict[str, Any]:
    """Sales for a period. Briefly cached — see ``SALES_CACHE_SECONDS``."""
    key = SALES_REPORT_KEY.format(branch=branch.pk, start=window.start, end=window.end)
    if refresh:
        from apps.core.cache import invalidate

        invalidate(key)
    return cached(key, SALES_CACHE_SECONDS, lambda: _sales(branch, window))


def _sales(branch: Any, window: Period) -> dict[str, Any]:
    from apps.payments.models import Refund, RefundStatus

    orders = counted_orders(branch, window)
    start, end = window.bounds

    #: Prep time is only meaningful when both stamps exist and run forwards.
    timed = Q(
        accepted_at__isnull=False,
        ready_at__isnull=False,
        ready_at__gte=F("accepted_at"),
    )
    totals = orders.aggregate(
        orders=Count("id"),
        gross=Sum("grand_total"),
        subtotal=Sum("subtotal"),
        discounts=Sum("discount_total"),
        delivery_fees=Sum("delivery_fee"),
        service_charges=Sum("service_charge"),
        vat=Sum("vat_total"),
        tips=Sum("tip"),
        prep_total=Sum(
            F("ready_at") - F("accepted_at"), filter=timed, output_field=DurationField()
        ),
        prep_count=Count("id", filter=timed),
    )
    prep_total = totals.pop("prep_total")
    prep_count = totals.pop("prep_count") or 0
    totals = {key: value or 0 for key, value in totals.items()}

    refunds = (
        Refund.objects.filter(
            order__branch=branch,
            status=RefundStatus.SUCCESS,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Every day in the window is present even when nothing was sold, so a chart
    # has no gaps. The database returns only the days that have rows.
    daily: dict[dt.date, dict[str, int]] = {
        day: {"orders": 0, "gross": 0} for day in window.dates()
    }
    for row in (
        orders.order_by()
        .annotate(day=TruncDate("placed_at", tzinfo=window.tz))
        .values("day")
        .annotate(count=Count("id"), gross=Sum("grand_total"))
    ):
        if row["day"] in daily:
            daily[row["day"]] = {"orders": row["count"], "gross": row["gross"] or 0}

    incomplete = dict(
        Order.objects.filter(
            branch=branch, placed_at__gte=start, placed_at__lt=end, status__in=INCOMPLETE_STATUSES
        )
        .order_by()
        .values_list("status")
        .annotate(total=Count("id"))
    )

    return {
        **totals,
        "refunds": refunds,
        "net": totals["gross"] - refunds,
        "average_order": totals["gross"] // totals["orders"] if totals["orders"] else 0,
        "average_prep_minutes": _average_minutes(prep_total, prep_count),
        "by_payment_method": _grouped(orders, "payment_method"),
        "by_fulfilment": _grouped(orders, "fulfilment_type"),
        "incomplete_orders": {status: incomplete.get(status, 0) for status in INCOMPLETE_STATUSES},
        "daily": [{"date": day, **values} for day, values in daily.items()],
    }


def _grouped(orders: QuerySet[Order], field: str) -> dict[str, dict[str, int]]:
    """Order count and gross, grouped by one column.

    ``.order_by()`` clears any default ordering first: a model's ``Meta.ordering``
    columns are added to the ``GROUP BY``, which would silently split every
    bucket into one row per order.
    """
    return {
        row[field]: {"orders": row["count"], "gross": row["gross"] or 0}
        for row in orders.order_by()
        .values(field)
        .annotate(count=Count("id"), gross=Sum("grand_total"))
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
    """Orders by local weekday and hour.

    One grouped query. ``ExtractIsoWeekDay`` is 1 = Monday on every backend,
    which is Python's ``weekday()`` plus one — unlike ``ExtractWeekDay``, which
    starts on Sunday.
    """
    grid = [[0] * 24 for _ in WEEKDAYS]
    rows = (
        counted_orders(branch, window)
        .order_by()
        .annotate(
            weekday=ExtractIsoWeekDay("placed_at", tzinfo=window.tz),
            hour=ExtractHour("placed_at", tzinfo=window.tz),
        )
        .values("weekday", "hour")
        .annotate(total=Count("id"))
    )
    for row in rows:
        if row["weekday"] is None or row["hour"] is None:  # pragma: no cover - range filter
            continue
        grid[row["weekday"] - 1][row["hour"]] += row["total"]

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

    Three queries whatever the volume: one aggregate over the assignments, one
    over the failed-delivery events, and one to put names to the riders that
    turned up in either.
    """
    from apps.delivery.models import DeliveryAssignment, RiderProfile

    start, end = window.bounds
    began = Coalesce("picked_up_at", "assigned_at")
    #: A hand-over recorded as happening before the pick-up is a data-entry
    #: error, not a negative delivery time; it is left out of the average.
    measurable = Q(delivered_at__gte=began)
    on_estimate = Q(order__estimated_delivery_at__isnull=False)

    rows = list(
        DeliveryAssignment.objects.filter(
            order__branch=branch, delivered_at__gte=start, delivered_at__lt=end
        )
        .order_by()
        .values("rider_id")
        .annotate(
            deliveries=Count("id"),
            cash=Coalesce(Sum("cash_collected"), Value(0)),
            estimated=Count("id", filter=on_estimate),
            on_time=Count(
                "id",
                filter=on_estimate & Q(delivered_at__lte=F("order__estimated_delivery_at")),
            ),
            timed_total=Sum(
                F("delivered_at") - began, filter=measurable, output_field=DurationField()
            ),
            timed_count=Count("id", filter=measurable),
        )
    )

    failures = dict(
        OrderStatusEvent.objects.filter(
            order__branch=branch,
            to_status=OrderStatus.FAILED_DELIVERY,
            created_at__gte=start,
            created_at__lt=end,
            order__delivery_assignment__isnull=False,
        )
        .order_by()
        .values_list("order__delivery_assignment__rider_id")
        .annotate(total=Count("id"))
    )

    rider_ids = {row["rider_id"] for row in rows} | set(failures)
    names = {
        profile.pk: profile.user.get_full_name()
        for profile in RiderProfile.objects.filter(pk__in=rider_ids).select_related("user")
    }

    def blank(rider_id: Any) -> dict[str, Any]:
        return {
            "rider": names.get(rider_id, ""),
            "deliveries": 0,
            "failed": 0,
            "cash_collected": 0,
            "average_delivery_minutes": None,
            "on_time_percent": None,
        }

    stats: dict[Any, dict[str, Any]] = {}
    for row in rows:
        rider_id = row["rider_id"]
        stats[rider_id] = {
            **blank(rider_id),
            "deliveries": row["deliveries"],
            "cash_collected": row["cash"] or 0,
            "average_delivery_minutes": _average_minutes(row["timed_total"], row["timed_count"]),
            "on_time_percent": (
                round(row["on_time"] * 100 / row["estimated"]) if row["estimated"] else None
            ),
        }
    for rider_id, count in failures.items():
        stats.setdefault(rider_id, blank(rider_id))["failed"] = count

    return sorted(stats.values(), key=lambda row: (-row["deliveries"], row["rider"]))
