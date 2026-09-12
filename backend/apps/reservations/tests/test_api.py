"""Reservation API."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from django.urls import reverse

from apps.reservations.models import Reservation, ReservationStatus

pytestmark = pytest.mark.django_db


def payload(booking_time, **overrides):  # type: ignore[no-untyped-def]
    return {
        "area": "indoor",
        "date": booking_time.date().isoformat(),
        "time": booking_time.strftime("%H:%M"),
        "party_size": 2,
        "guest_name": "Ada Obi",
        "guest_email": "ada@example.com",
        "guest_phone": "+2348012345678",
        **overrides,
    }


def create(api_client, booking_time, key=None, **overrides):  # type: ignore[no-untyped-def]
    return api_client.post(
        reverse("v1:reservations:create"),
        payload(booking_time, **overrides),
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
    )


# ── Areas and availability ────────────────────────────────────────────────────


def test_areas_are_listed(api_client, dining_room) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(reverse("v1:reservations:areas")).json()
    assert body[0]["slug"] == "indoor"
    assert body[0]["surcharge"]["display"] == "₦0.00"


def test_availability_reports_real_slots(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(
        reverse("v1:reservations:availability"),
        {"date": booking_time.date().isoformat(), "party_size": 2, "area": "indoor"},
    ).json()

    assert body["party_size"] == 2
    times = [slot["time"] for slot in body["slots"]]
    assert times[0] == "18:00"
    assert all(slot["tables_left"] == 2 for slot in body["slots"] if slot["available"])


def test_availability_reports_why_a_slot_is_closed(  # type: ignore[no-untyped-def]
    api_client, dining_room, booking_time
) -> None:
    """The UI can say "fully booked" rather than greying a button out silently."""
    create(api_client, booking_time)
    create(api_client, booking_time, guest_email="b@example.com")

    body = api_client.get(
        reverse("v1:reservations:availability"),
        {"date": booking_time.date().isoformat(), "party_size": 2},
    ).json()
    slot = next(s for s in body["slots"] if s["time"] == "19:00")
    assert slot["available"] is False
    assert slot["reason"] == "fully_booked"


def test_a_malformed_date_falls_back_to_today(api_client, dining_room) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:reservations:availability"), {"date": "not-a-date"})
    assert response.status_code == 200


# ── Booking ───────────────────────────────────────────────────────────────────


def test_booking_returns_a_reference_and_token(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    response = create(api_client, booking_time)
    assert response.status_code == 201

    body = response.json()
    assert body["reference"].startswith("RSV-")
    assert body["status"] == "confirmed"
    assert body["table_number"]
    assert body["confirmation_token"]


def test_an_idempotency_key_is_required(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:reservations:create"), payload(booking_time), format="json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


def test_a_double_submit_books_one_table(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """A double-tapped Confirm must not take two of the restaurant's tables."""
    key = str(uuid.uuid4())
    first = create(api_client, booking_time, key=key)
    second = create(api_client, booking_time, key=key)

    assert first.json()["reference"] == second.json()["reference"]
    assert second["Idempotency-Replayed"] == "true"
    assert Reservation.objects.count() == 1


def test_a_failed_attempt_releases_the_key(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    key = str(uuid.uuid4())
    bad = create(api_client, booking_time, key=key, party_size=0)
    assert bad.status_code == 400

    good = create(api_client, booking_time, key=key)
    assert good.status_code == 201


def test_a_full_slot_returns_409(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    create(api_client, booking_time, guest_email="a@example.com")
    create(api_client, booking_time, guest_email="b@example.com")

    response = create(api_client, booking_time, guest_email="c@example.com")
    assert response.status_code == 409
    assert response.json()["code"] == "slot_unavailable"


def test_an_unknown_area_is_404(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    assert create(api_client, booking_time, area="rooftop").status_code == 404


# ── Access control ────────────────────────────────────────────────────────────


def test_a_guest_needs_the_token_to_view(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = create(api_client, booking_time).json()
    url = reverse("v1:reservations:detail", kwargs={"reference": body["reference"]})

    assert api_client.get(url).status_code == 404
    assert (
        api_client.get(url, HTTP_X_RESERVATION_TOKEN=body["confirmation_token"]).status_code == 200
    )
    assert api_client.get(url, HTTP_X_RESERVATION_TOKEN="wrong").status_code == 404


def test_the_token_also_works_as_a_query_parameter(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """The emailed link carries it in the URL."""
    body = create(api_client, booking_time).json()
    url = reverse("v1:reservations:detail", kwargs={"reference": body["reference"]})
    assert api_client.get(url, {"token": body["confirmation_token"]}).status_code == 200


def test_a_signed_in_customer_sees_their_own(
    api_client, dining_room, booking_time, verified_user
) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    reference = create(api_client, booking_time).json()["reference"]

    url = reverse("v1:reservations:detail", kwargs={"reference": reference})
    assert api_client.get(url).status_code == 200

    body = api_client.get(reverse("v1:reservations:mine")).json()
    assert [row["reference"] for row in body] == [reference]


def test_another_customer_cannot_see_it(
    api_client, dining_room, booking_time, verified_user, db
) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    api_client.force_authenticate(user=verified_user)
    reference = create(api_client, booking_time).json()["reference"]

    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=intruder)
    url = reverse("v1:reservations:detail", kwargs={"reference": reference})
    assert api_client.get(url).status_code == 404


def test_staff_can_see_any_booking(api_client, dining_room, booking_time, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    reference = create(api_client, booking_time).json()["reference"]
    api_client.force_authenticate(user=kitchen_user)
    url = reverse("v1:reservations:detail", kwargs={"reference": reference})
    assert api_client.get(url).status_code == 200


# ── Reschedule and cancel ─────────────────────────────────────────────────────


def test_rescheduling_through_the_api(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = create(api_client, booking_time).json()
    later = booking_time + dt.timedelta(days=1)

    response = api_client.patch(
        reverse("v1:reservations:detail", kwargs={"reference": body["reference"]}),
        {"date": later.date().isoformat(), "time": later.strftime("%H:%M"), "party_size": 3},
        format="json",
        HTTP_X_RESERVATION_TOKEN=body["confirmation_token"],
    )
    assert response.status_code == 200
    assert response.json()["party_size"] == 3


def test_cancelling_through_the_api(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = create(api_client, booking_time).json()
    response = api_client.post(
        reverse("v1:reservations:cancel", kwargs={"reference": body["reference"]}),
        {"reason": "Plans changed"},
        format="json",
        HTTP_X_RESERVATION_TOKEN=body["confirmation_token"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == ReservationStatus.CANCELLED


def test_a_stranger_cannot_cancel(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = create(api_client, booking_time).json()
    response = api_client.post(
        reverse("v1:reservations:cancel", kwargs={"reference": body["reference"]}),
        {},
        format="json",
    )
    assert response.status_code == 404
    assert Reservation.objects.get().status == ReservationStatus.CONFIRMED


# ── Staff book ────────────────────────────────────────────────────────────────


def test_the_days_book_requires_staff(api_client, dining_room, booking_time, verified_user) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:reservations:todays-book")).status_code in (401, 403)

    api_client.force_authenticate(user=verified_user)
    assert api_client.get(reverse("v1:reservations:todays-book")).status_code == 403


def test_the_days_book_lists_covers(api_client, dining_room, booking_time, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    create(api_client, booking_time, party_size=2, guest_email="a@example.com")
    create(api_client, booking_time, party_size=4, guest_email="b@example.com")

    api_client.force_authenticate(user=kitchen_user)
    body = api_client.get(
        reverse("v1:reservations:todays-book"), {"date": booking_time.date().isoformat()}
    ).json()

    assert body["covers"] == 6
    assert len(body["reservations"]) == 2
    assert body["reservations"][0]["time"] == "19:00"


# ── Malformed input is ignored, not fatal ─────────────────────────────────────


def test_a_malformed_party_size_falls_back(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    """A stray character in a URL should not turn availability into a 400."""
    response = api_client.get(
        reverse("v1:reservations:availability"),
        {"date": booking_time.date().isoformat(), "party_size": "lots"},
    )
    assert response.status_code == 200
    assert response.json()["party_size"] == 2


def test_a_malformed_date_in_the_days_book_falls_back(
    api_client, dining_room, kitchen_user
) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.get(reverse("v1:reservations:todays-book"), {"date": "yesterday"})
    assert response.status_code == 200


def test_a_stranger_cannot_reschedule(api_client, dining_room, booking_time) -> None:  # type: ignore[no-untyped-def]
    body = create(api_client, booking_time).json()
    later = booking_time + dt.timedelta(days=1)

    response = api_client.patch(
        reverse("v1:reservations:detail", kwargs={"reference": body["reference"]}),
        {"date": later.date().isoformat(), "time": later.strftime("%H:%M")},
        format="json",
    )
    assert response.status_code == 404

    Reservation.objects.get().refresh_from_db()
    assert Reservation.objects.get().reserved_for == booking_time
