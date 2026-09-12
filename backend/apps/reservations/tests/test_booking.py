"""Booking, rescheduling and cancellation.

Replaces `app/reservations/page.tsx:116` — `alert("Reservation submitted!")`
with nothing recorded anywhere.
"""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections
from django.utils import timezone

from apps.notifications.models import Notification
from apps.reservations.models import Reservation, ReservationStatus
from apps.reservations.services import booking
from apps.reservations.services.booking import BookingRejected, SlotUnavailable
from conftest import requires_postgres

pytestmark = pytest.mark.django_db


def book(branch, area, when, size=2, email="ada@example.com", **kwargs):  # type: ignore[no-untyped-def]
    return booking.book(
        branch=branch,
        area=area,
        reserved_for=when,
        party_size=size,
        guest_name="Ada Obi",
        guest_email=email,
        guest_phone="+2348012345678",
        **kwargs,
    )


# ── Booking ───────────────────────────────────────────────────────────────────


def test_a_booking_is_recorded(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """The whole point: the restaurant now knows the customer is coming."""
    reservation = book(branch, dining_room, booking_time)

    assert Reservation.objects.count() == 1
    assert reservation.reference.startswith("RSV-")
    assert reservation.status == ReservationStatus.CONFIRMED
    assert reservation.table is not None
    assert reservation.duration_minutes == 120


def test_the_guest_is_emailed(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    email = Notification.objects.get(template_key="reservation_confirmed")
    assert email.recipient == "ada@example.com"
    assert reservation.reference in email.body
    assert "Indoor Seating" in email.body


def test_references_avoid_ambiguous_characters(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.models import generate_reference

    references = {generate_reference() for _ in range(300)}
    assert len(references) == 300
    assert not any(set("01OI") & set(ref[4:]) for ref in references)


def test_a_signed_in_customer_is_linked(branch, dining_room, booking_time, verified_user) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time, user=verified_user)
    assert reservation.user == verified_user


def test_a_guest_booking_has_no_user(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    assert book(branch, dining_room, booking_time).user is None


def test_booking_beyond_the_last_seating_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    late = booking_time.replace(hour=23, minute=0)
    with pytest.raises(BookingRejected, match="do not take bookings at that time"):
        book(branch, dining_room, late)


def test_booking_too_soon_is_refused(branch, dining_room) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(BookingRejected, match="notice"):
        book(branch, dining_room, timezone.now() + dt.timedelta(minutes=5))


def test_booking_too_far_ahead_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(BookingRejected, match="days ahead"):
        book(branch, dining_room, booking_time + dt.timedelta(days=200))


def test_a_zero_size_party_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(BookingRejected, match="at least one guest"):
        book(branch, dining_room, booking_time, size=0)


def test_a_full_house_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    book(branch, dining_room, booking_time, email="a@example.com")
    book(branch, dining_room, booking_time, email="b@example.com")

    with pytest.raises(SlotUnavailable, match="fully booked"):
        book(branch, dining_room, booking_time, email="c@example.com")


def test_a_full_area_suggests_elsewhere(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """ "This room is full but we have space" is more useful than a flat no."""
    from apps.reservations.models import RestaurantTable, TableArea

    patio = TableArea.objects.create(
        branch=branch, name="Outdoor Patio", slug="outdoor", display_order=2
    )
    RestaurantTable.objects.create(branch=branch, area=patio, number="P1", seats_min=1, seats_max=4)

    book(branch, dining_room, booking_time, email="a@example.com")
    book(branch, dining_room, booking_time, email="b@example.com")

    with pytest.raises(SlotUnavailable, match="space elsewhere"):
        book(branch, dining_room, booking_time, email="c@example.com")


def test_a_party_larger_than_any_table_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(SlotUnavailable):
        book(branch, dining_room, booking_time, size=40)


# ── The Gate 2 guarantee ──────────────────────────────────────────────────────


def test_two_bookings_never_share_a_table(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """Sequential proof. The concurrent proof is below, on Postgres."""
    first = book(branch, dining_room, booking_time, email="a@example.com")
    second = book(branch, dining_room, booking_time, email="b@example.com")
    assert first.table_id != second.table_id


def test_an_overlapping_booking_cannot_reuse_the_table(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    """The 120-minute turn is honoured, not just the start time."""
    book(branch, dining_room, booking_time, email="a@example.com")
    book(branch, dining_room, booking_time, email="b@example.com")

    overlapping = booking_time + dt.timedelta(minutes=30)
    with pytest.raises(SlotUnavailable):
        book(branch, dining_room, overlapping, email="c@example.com")


@requires_postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_cannot_double_book(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """**Gate 2.** Six people booking the last two tables at the same instant.

    Two succeed, four are told the slot is gone, and no table is ever booked
    twice. Guarded by a row lock in the service and, authoritatively, by the
    Postgres exclusion constraint in migration 0002.
    """

    def attempt(index: int) -> str:
        try:
            book(branch, dining_room, booking_time, email=f"guest{index}@example.com")
            return "booked"
        except SlotUnavailable:
            return "refused"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(6)))

    assert results.count("booked") == 2, results
    confirmed = Reservation.objects.filter(status=ReservationStatus.CONFIRMED)
    assert confirmed.count() == 2
    assert len({r.table_id for r in confirmed}) == 2  # two distinct tables


# ── Rescheduling ──────────────────────────────────────────────────────────────


def test_rescheduling_keeps_the_reference(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    later = booking_time + dt.timedelta(days=1)

    booking.reschedule(reservation=reservation, reserved_for=later)

    reservation.refresh_from_db()
    assert reservation.reserved_for == later
    assert Reservation.objects.count() == 1


def test_rescheduling_frees_the_original_slot(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.services.availability import slots_for

    first = book(branch, dining_room, booking_time, email="a@example.com")
    book(branch, dining_room, booking_time, email="b@example.com")

    booking.reschedule(reservation=first, reserved_for=booking_time + dt.timedelta(days=1))

    slot = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == dt.time(19, 0)
    )
    assert slot.available is True


def test_rescheduling_into_a_full_slot_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    target = booking_time + dt.timedelta(days=1)
    book(branch, dining_room, target, email="a@example.com")
    book(branch, dining_room, target, email="b@example.com")
    mine = book(branch, dining_room, booking_time, email="c@example.com")

    with pytest.raises(SlotUnavailable):
        booking.reschedule(reservation=mine, reserved_for=target)


def test_rescheduling_emails_the_guest(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    booking.reschedule(reservation=reservation, reserved_for=booking_time + dt.timedelta(days=1))
    assert Notification.objects.filter(template_key="reservation_rescheduled").exists()


def test_a_cancelled_booking_cannot_be_rescheduled(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    booking.cancel(reservation=reservation)

    with pytest.raises(BookingRejected, match="no longer be changed"):
        booking.reschedule(reservation=reservation, reserved_for=booking_time)


# ── Cancellation and service states ───────────────────────────────────────────


def test_cancelling_records_the_reason_and_emails(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    booking.cancel(reservation=reservation, reason="Plans changed")

    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.CANCELLED
    assert reservation.cancellation_reason == "Plans changed"
    assert Notification.objects.filter(template_key="reservation_cancelled").exists()


def test_cancelling_twice_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    booking.cancel(reservation=reservation)
    with pytest.raises(BookingRejected):
        booking.cancel(reservation=reservation)


def test_service_states(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)

    booking.seat(reservation=reservation)
    assert reservation.status == ReservationStatus.SEATED
    assert reservation.occupies_a_table is True

    booking.complete(reservation=reservation)
    assert reservation.status == ReservationStatus.COMPLETED
    assert reservation.occupies_a_table is False


def test_a_no_show_frees_the_table_for_reporting(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    booking.mark_no_show(reservation=reservation)
    assert reservation.status == ReservationStatus.NO_SHOW
    assert reservation.occupies_a_table is False


# ── Remaining guards ──────────────────────────────────────────────────────────


def test_blackouts_are_enforced_at_booking_time_not_just_in_availability(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    """Hiding a slot in the UI is not the same as refusing the booking.

    A client that posts a time directly must still be turned away.
    """
    from apps.reservations.models import BlackoutDate

    BlackoutDate.objects.create(
        branch=branch, date=booking_time.date(), full_day=True, reason="Private event"
    )
    with pytest.raises(BookingRejected, match="Private event"):
        book(branch, dining_room, booking_time)


def test_a_partial_blackout_refuses_only_its_window(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.models import BlackoutDate

    BlackoutDate.objects.create(
        branch=branch,
        date=booking_time.date(),
        full_day=False,
        starts_at=dt.time(18, 0),
        ends_at=dt.time(19, 30),
        reason="Staff briefing",
    )
    with pytest.raises(BookingRejected, match="Staff briefing"):
        book(branch, dining_room, booking_time)

    later = booking_time.replace(hour=20, minute=0)
    assert book(branch, dining_room, later).reference


def test_a_blackout_with_no_reason_still_refuses(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.models import BlackoutDate

    BlackoutDate.objects.create(branch=branch, date=booking_time.date(), full_day=True)
    with pytest.raises(BookingRejected, match="closed that day"):
        book(branch, dining_room, booking_time)


def test_overlap_detection_with_no_candidate_tables(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.services.availability import overlapping_reservations

    assert (
        overlapping_reservations(
            tables=[], start=booking_time, end=booking_time + dt.timedelta(hours=2)
        )
        == set()
    )


def test_a_database_level_overlap_is_reported_as_a_lost_slot(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time, monkeypatch
) -> None:
    """If the exclusion constraint fires, the customer sees "taken", not a 500.

    Simulated here because SQLite has no such constraint (ADR-015); on Postgres
    it is the real backstop.
    """
    from django.db import IntegrityError

    from apps.reservations.models import Reservation as ReservationModel

    def explode(*args: object, **kwargs: object) -> None:
        raise IntegrityError("no_double_booked_table")

    monkeypatch.setattr(ReservationModel.objects, "create", explode)

    with pytest.raises(SlotUnavailable, match="taken while you were booking"):
        book(branch, dining_room, booking_time)


def test_rescheduling_to_an_impossible_time_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    with pytest.raises(BookingRejected, match="notice"):
        booking.reschedule(
            reservation=reservation, reserved_for=timezone.now() + dt.timedelta(minutes=5)
        )


def test_rescheduling_to_a_party_too_large_is_refused(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    reservation = book(branch, dining_room, booking_time)
    with pytest.raises(SlotUnavailable):
        booking.reschedule(reservation=reservation, reserved_for=booking_time, party_size=40)


def test_turn_time_falls_back_when_no_period_matches(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """A sensible default beats a crash if the schedule has a gap."""
    from apps.reservations.services.availability import turn_time_for

    assert turn_time_for(branch, booking_time.replace(hour=4)) == 90
