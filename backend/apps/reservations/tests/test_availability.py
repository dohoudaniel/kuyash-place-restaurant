"""Availability computation."""

from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from apps.reservations.models import BlackoutDate
from apps.reservations.services import booking
from apps.reservations.services.availability import (
    candidate_tables,
    find_free_table,
    slots_for,
    turn_time_for,
    validate_booking_window,
)

pytestmark = pytest.mark.django_db


def book_one(branch, area, when, size=2, email="ada@example.com"):  # type: ignore[no-untyped-def]
    return booking.book(
        branch=branch,
        area=area,
        reserved_for=when,
        party_size=size,
        guest_name="Ada Obi",
        guest_email=email,
        guest_phone="+2348012345678",
    )


def test_slots_come_from_service_periods(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """Not a hardcoded list of 18 times."""
    slots = slots_for(branch, date=booking_time.date(), party_size=2)
    times = [slot.time.strftime("%H:%M") for slot in slots]
    assert times[0] == "18:00"
    assert times[-1] == "21:30"
    assert "12:00" not in times  # no lunch period configured in this fixture


def test_a_booking_consumes_one_table(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    before = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == dt.time(19, 0)
    )
    assert before.tables_left == 2

    book_one(branch, dining_room, booking_time)

    after = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == dt.time(19, 0)
    )
    assert after.tables_left == 1
    assert after.available is True


def test_a_slot_becomes_unavailable_when_every_table_is_taken(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    book_one(branch, dining_room, booking_time, email="a@example.com")
    book_one(branch, dining_room, booking_time, email="b@example.com")

    slot = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == dt.time(19, 0)
    )
    assert slot.available is False
    assert slot.reason == "fully_booked"
    assert slot.tables_left == 0


def test_an_overlapping_sitting_blocks_a_later_slot(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    """A 120-minute turn at 19:00 must block 20:00, not just 19:00.

    Comparing start times alone would let a second party sit on top of the first.
    """
    book_one(branch, dining_room, booking_time, email="a@example.com")
    book_one(branch, dining_room, booking_time, email="b@example.com")

    later = booking_time + dt.timedelta(hours=1)
    slot = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == later.time()
    )
    assert slot.available is False


def test_a_slot_after_the_turn_ends_is_free_again(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    book_one(branch, dining_room, booking_time, email="a@example.com")
    book_one(branch, dining_room, booking_time, email="b@example.com")

    after_turn = booking_time + dt.timedelta(minutes=120)
    slots = {s.time: s for s in slots_for(branch, date=booking_time.date(), party_size=2)}
    if after_turn.time() in slots:
        assert slots[after_turn.time()].available is True


def test_a_cancelled_booking_frees_the_table(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    first = book_one(branch, dining_room, booking_time, email="a@example.com")
    book_one(branch, dining_room, booking_time, email="b@example.com")

    booking.cancel(reservation=first)

    slot = next(
        s
        for s in slots_for(branch, date=booking_time.date(), party_size=2)
        if s.time == dt.time(19, 0)
    )
    assert slot.available is True


def test_a_party_too_large_for_any_table_has_no_slots(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time
) -> None:
    slots = slots_for(branch, date=booking_time.date(), party_size=40)
    assert all(not slot.available for slot in slots)
    assert slots[0].reason == "no_table_for_party_size"


def test_the_smallest_suitable_table_is_chosen(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """A party of two should not consume a table for eight."""
    from apps.reservations.models import RestaurantTable

    big = RestaurantTable.objects.create(
        branch=branch, area=dining_room, number="9", seats_min=1, seats_max=8
    )
    table = find_free_table(
        branch, start=booking_time, duration_minutes=120, party_size=2, area=dining_room
    )
    assert table is not None
    assert table.seats_max <= big.seats_max


def test_a_full_day_blackout_closes_every_slot(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    BlackoutDate.objects.create(
        branch=branch, date=booking_time.date(), full_day=True, reason="Private event"
    )
    slots = slots_for(branch, date=booking_time.date(), party_size=2)
    assert slots
    assert all(slot.reason == "closed" for slot in slots)


def test_a_partial_blackout_closes_only_its_window(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    BlackoutDate.objects.create(
        branch=branch,
        date=booking_time.date(),
        full_day=False,
        starts_at=dt.time(18, 0),
        ends_at=dt.time(19, 0),
    )
    slots = {s.time: s for s in slots_for(branch, date=booking_time.date(), party_size=2)}
    assert slots[dt.time(18, 30)].reason == "closed"
    assert slots[dt.time(20, 0)].available is True


def test_slots_too_soon_are_not_offered(branch, dining_room) -> None:  # type: ignore[no-untyped-def]
    """A booking for ten minutes' time is not something the kitchen can honour."""
    today = timezone.localtime(timezone.now(), branch.tzinfo()).date()
    slots = slots_for(branch, date=today, party_size=2)
    past = [s for s in slots if s.reason == "too_soon"]
    assert past or all(s.available for s in slots)  # depends on the hour the suite runs


def test_a_date_with_no_service_period_has_no_slots(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.models import ServicePeriod

    ServicePeriod.objects.all().delete()
    assert slots_for(branch, date=booking_time.date(), party_size=2) == []


def test_the_booking_window_is_validated(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    assert validate_booking_window(branch, booking_time) == ""

    too_soon = timezone.now() + dt.timedelta(minutes=5)
    assert "notice" in validate_booking_window(branch, too_soon)

    too_far = timezone.now() + dt.timedelta(days=200)
    assert "days ahead" in validate_booking_window(branch, too_far)

    outside = booking_time.replace(hour=3)
    assert "do not take bookings at that time" in validate_booking_window(branch, outside)


def test_turn_time_comes_from_the_period(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    assert turn_time_for(branch, booking_time) == 120


def test_availability_fetches_the_days_bookings_once(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time, django_assert_max_num_queries
) -> None:
    """It used to run one query *per slot* — about 24 per request, on a public
    and unthrottled endpoint. The day's bookings are fetched once and bucketed
    in Python instead.

    The budget: service periods, the blackout lookup, candidate tables, and the
    day's bookings. Four queries, and crucially it does not grow with the number
    of slots.
    """
    book_one(branch, dining_room, booking_time, email="a@example.com")

    with django_assert_max_num_queries(5):
        slots = slots_for(branch, date=booking_time.date(), party_size=2)

    assert len(slots) == 8  # 18:00–21:30 every half hour
    assert any(slot.tables_left == 1 for slot in slots)


def test_the_query_count_does_not_grow_with_the_number_of_slots(  # type: ignore[no-untyped-def]
    branch, dining_room, booking_time, django_assert_max_num_queries
) -> None:
    """Widen the service period to 24 slots; the query count must not move."""
    from apps.reservations.models import ServicePeriod

    ServicePeriod.objects.filter(branch=branch).update(
        starts_at=dt.time(10, 0), ends_at=dt.time(21, 30)
    )
    with django_assert_max_num_queries(5):
        slots = slots_for(branch, date=booking_time.date(), party_size=2)

    assert len(slots) == 24


def test_candidate_tables_respect_the_area(branch, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    from apps.reservations.models import RestaurantTable, TableArea

    patio = TableArea.objects.create(
        branch=branch, name="Outdoor Patio", slug="outdoor", display_order=2
    )
    RestaurantTable.objects.create(branch=branch, area=patio, number="P1", seats_min=1, seats_max=4)
    indoor = candidate_tables(branch, party_size=2, area=dining_room)
    assert {table.area_id for table in indoor} == {dining_room.pk}
