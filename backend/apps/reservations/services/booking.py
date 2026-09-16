"""Booking, rescheduling and cancellation.

The double-booking guarantee has two layers:

1. **Application**: table allocation happens inside a transaction that takes a
   row lock on the candidate tables, so two concurrent bookings cannot pick the
   same table.
2. **Database** (Postgres only): an ``ExclusionConstraint`` over
   ``(table, time range)`` refuses an overlap outright, whatever the
   application believes. SQLite has no equivalent (ADR-015), so locally layer 1
   is the only guard and the concurrency test is skipped there — CI runs it
   against Postgres.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.exceptions import DomainError
from apps.reservations.models import (
    Reservation,
    ReservationSource,
    ReservationStatus,
    RestaurantTable,
    TableArea,
)
from apps.reservations.services.availability import (
    find_free_table,
    turn_time_for,
    validate_booking_window,
)

logger = logging.getLogger(__name__)


class SlotUnavailable(DomainError):
    code = "slot_unavailable"
    title = "That time is no longer available"
    status_code = 409


class BookingRejected(DomainError):
    code = "booking_rejected"
    title = "That booking cannot be made"
    status_code = 422


def _lock_candidate_tables(  # pragma: no cover - Postgres only; runs in the Postgres CI job
    branch: Any, party_size: int, area: TableArea | None
) -> None:
    """Take row locks on every table that could seat this party."""
    queryset = RestaurantTable.objects.filter(
        branch=branch, is_active=True, seats_min__lte=party_size, seats_max__gte=party_size
    )
    if area is not None:
        queryset = queryset.filter(area=area)
    list(queryset.select_for_update().values_list("pk", flat=True))


def _lock_tables(branch: Any, party_size: int, area: TableArea | None) -> None:
    """Serialise allocation for this party size.

    On Postgres this takes row locks so two concurrent bookings cannot both
    believe the same table is free. SQLite has no row locking (ADR-015); the
    surrounding transaction is the best it offers, and the concurrency test is
    skipped there.
    """
    if not settings.USING_POSTGRES:
        return
    _lock_candidate_tables(branch, party_size, area)


@transaction.atomic
def book(
    *,
    branch: Any,
    area: TableArea,
    reserved_for: dt.datetime,
    party_size: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str,
    user: Any = None,
    special_requests: str = "",
    source: str = ReservationSource.WEB,
    idempotency_key: str = "",
) -> Reservation:
    """Reserve a table, or refuse and say why."""
    if party_size < 1:
        raise BookingRejected("A booking needs at least one guest.")

    window_error = validate_booking_window(branch, reserved_for)
    if window_error:
        raise BookingRejected(window_error)

    duration = turn_time_for(branch, reserved_for)

    _lock_tables(branch, party_size, area)
    table = find_free_table(
        branch,
        start=reserved_for,
        duration_minutes=duration,
        party_size=party_size,
        area=area,
    )
    if table is None:
        # Distinguish "no table that size exists" from "all of them are taken":
        # the first is a dead end, the second means try another time.
        any_table = find_free_table(
            branch, start=reserved_for, duration_minutes=duration, party_size=party_size
        )
        if any_table is not None:
            raise SlotUnavailable(
                f"{area.name} is fully booked then, but we have space elsewhere.",
                area=area.slug,
            )
        raise SlotUnavailable("That time is fully booked. Please choose another.")

    try:
        # A savepoint, so an IntegrityError leaves the surrounding transaction
        # usable: on Postgres the follow-up query below would otherwise raise
        # TransactionManagementError instead of answering.
        with transaction.atomic():
            reservation = Reservation.objects.create(
                branch=branch,
                user=user
                if user is not None and getattr(user, "is_authenticated", False)
                else None,
                area=area,
                table=table,
                reserved_for=reserved_for,
                duration_minutes=duration,
                party_size=party_size,
                guest_name=guest_name.strip(),
                guest_email=guest_email.strip().lower(),
                guest_phone=guest_phone.strip(),
                special_requests=special_requests.strip(),
                source=source,
                idempotency_key=idempotency_key,
            )
    except IntegrityError as exc:
        # Two different constraints can land here.
        if idempotency_key:
            replayed = Reservation.objects.filter(idempotency_key=idempotency_key).first()
            if replayed is not None:
                # The unique key caught a duplicate the cache let through — an
                # eviction, a flush, a Redis failover. The customer gets their
                # original booking back rather than a second table or a 500,
                # which is the entire point of having a database backstop.
                logger.warning(
                    "reservation_idempotency_replayed_from_database",
                    extra={"reservation": replayed.reference},
                )
                return replayed
        # Otherwise the exclusion constraint caught an overlap the application
        # missed — a genuine race. Report it as a lost slot, not a 500.
        logger.warning("reservation_overlap_rejected_by_database", extra={"table": table.pk})
        raise SlotUnavailable("That table was taken while you were booking.") from exc

    _notify(reservation, "reservation_confirmed")
    return reservation


@transaction.atomic
def reschedule(
    *, reservation: Reservation, reserved_for: dt.datetime, party_size: int | None = None
) -> Reservation:
    """Move a booking, keeping its reference."""
    if not reservation.can_cancel:
        raise BookingRejected("This booking can no longer be changed online.")

    branch = reservation.branch
    size = party_size or reservation.party_size

    window_error = validate_booking_window(branch, reserved_for)
    if window_error:
        raise BookingRejected(window_error)

    duration = turn_time_for(branch, reserved_for)
    _lock_tables(branch, size, reservation.area)
    table = find_free_table(
        branch,
        start=reserved_for,
        duration_minutes=duration,
        party_size=size,
        area=reservation.area,
        exclude_reservation=reservation,
    )
    if table is None:
        raise SlotUnavailable("That time is fully booked. Please choose another.")

    reservation.reserved_for = reserved_for
    reservation.duration_minutes = duration
    reservation.party_size = size
    reservation.table = table
    try:
        with transaction.atomic():
            reservation.save()
    except IntegrityError as exc:
        # book() has always handled this; reschedule() did not, so losing the
        # same race here returned a 500 rather than "that time just went".
        logger.warning(
            "reservation_overlap_rejected_by_database_on_reschedule",
            extra={"table": table.pk},
        )
        raise SlotUnavailable("That table was taken while you were rescheduling.") from exc

    _notify(reservation, "reservation_rescheduled")
    return reservation


def cancel(*, reservation: Reservation, reason: str = "", actor: Any = None) -> Reservation:
    """Release the table."""
    if not reservation.can_cancel:
        raise BookingRejected("This booking has already been completed or cancelled.")

    reservation.status = ReservationStatus.CANCELLED
    reservation.cancellation_reason = reason.strip()
    reservation.save(update_fields=["status", "cancellation_reason", "updated_at"])

    _notify(reservation, "reservation_cancelled")
    return reservation


def mark_no_show(*, reservation: Reservation) -> Reservation:
    reservation.status = ReservationStatus.NO_SHOW
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


def seat(*, reservation: Reservation) -> Reservation:
    reservation.status = ReservationStatus.SEATED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


def complete(*, reservation: Reservation) -> Reservation:
    reservation.status = ReservationStatus.COMPLETED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


def _notify(reservation: Reservation, template_key: str) -> None:
    """Email the guest. A booking nobody is told about is the current bug."""
    from apps.notifications.services import queue_templated_email

    local = timezone.localtime(reservation.reserved_for, reservation.branch.tzinfo())
    manage_url = (
        f"{settings.FRONTEND_URL}/reservations/{reservation.reference}"
        f"?token={reservation.confirmation_token}"
    )
    queue_templated_email(
        template_key=template_key,
        recipient=reservation.guest_email,
        context={
            "name": reservation.guest_name.split(" ")[0] or "there",
            "reference": reservation.reference,
            "date": local.strftime("%A %d %B %Y"),
            "time": local.strftime("%H:%M"),
            "party_size": reservation.party_size,
            "area": reservation.area.name,
            "manage_url": manage_url,
        },
    )
