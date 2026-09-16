"""Availability.

Slots are *computed* from service periods, table capacity and live bookings.
The frontend hardcodes 18 always-available times, which is only safe because
nothing it offers can ever actually be booked.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.reservations.models import (
    OCCUPYING_STATUSES,
    BlackoutDate,
    Reservation,
    RestaurantTable,
    ServicePeriod,
    TableArea,
)

#: How far ahead bookings are accepted.
MAX_ADVANCE_DAYS = 90
#: How soon before a sitting a booking may still be made.
MIN_LEAD_MINUTES = 30


@dataclass(frozen=True, slots=True)
class Slot:
    """One bookable start time."""

    time: dt.time
    available: bool
    tables_left: int
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "time": self.time.strftime("%H:%M"),
            "available": self.available,
            "tables_left": self.tables_left,
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


def _aware(branch: Any, date: dt.date, time: dt.time) -> dt.datetime:
    return dt.datetime.combine(date, time, tzinfo=branch.tzinfo())


def candidate_tables(
    branch: Any, *, party_size: int, area: TableArea | None = None
) -> list[RestaurantTable]:
    """Tables that can seat this party.

    Ordered smallest-first so a party of two does not consume a table for eight
    while one for two sits empty.
    """
    queryset = RestaurantTable.objects.filter(
        branch=branch, is_active=True, seats_min__lte=party_size, seats_max__gte=party_size
    ).select_related("area")
    if area is not None:
        queryset = queryset.filter(area=area)
    return list(queryset.order_by("seats_max", "number"))


def overlapping_reservations(
    *, tables: list[RestaurantTable], start: dt.datetime, end: dt.datetime
) -> set[Any]:
    """IDs of tables already occupied for any part of ``start``–``end``.

    Two bookings overlap when each starts before the other ends. Comparing only
    start times would let a 19:00 booking sit on top of an 18:30 one.
    """
    if not tables:
        return set()
    clashes = Reservation.objects.filter(table__in=tables, status__in=OCCUPYING_STATUSES).filter(
        reserved_for__lt=end
    )

    occupied: set[Any] = set()
    for reservation in clashes.only("table_id", "reserved_for", "duration_minutes"):
        if reservation.ends_at > start:
            occupied.add(reservation.table_id)
    return occupied


def find_free_table(
    branch: Any,
    *,
    start: dt.datetime,
    duration_minutes: int,
    party_size: int,
    area: TableArea | None = None,
    exclude_reservation: Any = None,
) -> RestaurantTable | None:
    """The smallest suitable table free for the whole sitting, or ``None``."""
    tables = candidate_tables(branch, party_size=party_size, area=area)
    if not tables:
        return None

    end = start + dt.timedelta(minutes=duration_minutes)
    clashes = Reservation.objects.filter(
        table__in=tables, status__in=OCCUPYING_STATUSES, reserved_for__lt=end
    )
    if exclude_reservation is not None:
        clashes = clashes.exclude(pk=exclude_reservation.pk)

    occupied = {
        reservation.table_id
        for reservation in clashes.only("table_id", "reserved_for", "duration_minutes")
        if reservation.ends_at > start
    }
    return next((table for table in tables if table.pk not in occupied), None)


def blackout_for(branch: Any, date: dt.date) -> BlackoutDate | None:
    return BlackoutDate.objects.filter(branch=branch, date=date).first()


def _bookings_for_day(
    branch: Any,
    date: dt.date,
    *,
    tables: list[RestaurantTable],
    schedule: list[tuple[ServicePeriod, list[dt.time]]],
) -> list[Reservation]:
    """Every booking that could clash with any slot in the day — in one query.

    Availability used to run ``overlapping_reservations`` per slot: about 24
    queries per request, on a public and unthrottled endpoint, which is the
    cheapest denial-of-service in the codebase. The day's bookings are few, so
    fetching them once and bucketing in Python is strictly better.

    The upper bound is the end of the last sitting offered. There is no lower
    bound: a long turn that started earlier can still cover the first slot, and
    the ``(table, reserved_for)`` index keeps the scan cheap either way.
    """
    if not tables:
        return []
    ends = [
        _aware(branch, date, times[-1]) + dt.timedelta(minutes=period.turn_time_minutes)
        for period, times in schedule
        if times
    ]
    if not ends:
        return []
    return list(
        Reservation.objects.filter(
            table__in=tables, status__in=OCCUPYING_STATUSES, reserved_for__lt=max(ends)
        ).only("table_id", "reserved_for", "duration_minutes")
    )


def slots_for(
    branch: Any, *, date: dt.date, party_size: int, area: TableArea | None = None
) -> list[Slot]:
    """Every start time for a date, marked available or not, with the reason."""
    periods = ServicePeriod.objects.filter(
        branch=branch, weekday=date.weekday(), is_active=True
    ).order_by("starts_at")
    if not periods:
        return []

    schedule = [(period, period.slot_times()) for period in periods]

    blackout = blackout_for(branch, date)
    if blackout is not None and blackout.full_day:
        return [
            Slot(time=time, available=False, tables_left=0, reason="closed")
            for _period, times in schedule
            for time in times
        ]

    tables = candidate_tables(branch, party_size=party_size, area=area)
    now = timezone.now()
    earliest = now + dt.timedelta(minutes=MIN_LEAD_MINUTES)
    bookings = _bookings_for_day(branch, date, tables=tables, schedule=schedule)

    slots: list[Slot] = []
    for period, times in schedule:
        for time in times:
            start = _aware(branch, date, time)
            end = start + dt.timedelta(minutes=period.turn_time_minutes)

            if not tables:
                slots.append(Slot(time, False, 0, "no_table_for_party_size"))
                continue
            if start < earliest:
                slots.append(Slot(time, False, 0, "too_soon"))
                continue
            if blackout is not None and blackout.starts_at and blackout.ends_at:
                if blackout.starts_at <= time <= blackout.ends_at:
                    slots.append(Slot(time, False, 0, "closed"))
                    continue

            # Two bookings overlap when each starts before the other ends —
            # the same test overlapping_reservations applies, in memory.
            occupied = {
                booking.table_id
                for booking in bookings
                if booking.reserved_for < end and booking.ends_at > start
            }
            free = len(tables) - len(occupied)
            slots.append(
                Slot(
                    time=time,
                    available=free > 0,
                    tables_left=max(free, 0),
                    reason="" if free > 0 else "fully_booked",
                )
            )
    return slots


def validate_booking_window(branch: Any, start: dt.datetime) -> str:
    """Return an error message if this moment cannot be booked, else ``""``."""
    now = timezone.now()
    if start < now + dt.timedelta(minutes=MIN_LEAD_MINUTES):
        return (
            f"Bookings need at least {MIN_LEAD_MINUTES} minutes' notice. "
            "Please call us for anything sooner."
        )
    if start > now + dt.timedelta(days=MAX_ADVANCE_DAYS):
        return f"We take bookings up to {MAX_ADVANCE_DAYS} days ahead."

    local = start.astimezone(branch.tzinfo())
    periods = ServicePeriod.objects.filter(branch=branch, weekday=local.weekday(), is_active=True)
    if not periods.filter(Q(starts_at__lte=local.time()) & Q(ends_at__gte=local.time())).exists():
        return "We do not take bookings at that time."

    blackout = blackout_for(branch, local.date())
    if blackout is not None:
        if blackout.full_day:
            return blackout.reason or "We are closed that day."
        if blackout.starts_at and blackout.ends_at:
            if blackout.starts_at <= local.time() <= blackout.ends_at:
                return blackout.reason or "We are closed at that time."
    return ""


def turn_time_for(branch: Any, start: dt.datetime) -> int:
    """The sitting length configured for the period covering ``start``."""
    local = start.astimezone(branch.tzinfo())
    period = (
        ServicePeriod.objects.filter(
            branch=branch,
            weekday=local.weekday(),
            is_active=True,
            starts_at__lte=local.time(),
            ends_at__gte=local.time(),
        )
        .order_by("starts_at")
        .first()
    )
    return period.turn_time_minutes if period else 90
