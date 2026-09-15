"""What the kitchen screen needs from the API (ORDERS_AND_FULFILMENT.md §4)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.catalog.models import MenuItem
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import REJECT_REASONS
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    return transition(order, OrderStatus.PAID)


@pytest.fixture
def kitchen(api_client, kitchen_user):  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    return api_client


def rider(email: str, name: str, on_shift: bool):  # type: ignore[no-untyped-def]
    from apps.accounts.models import User
    from apps.delivery.models import RiderProfile, VehicleType

    user = User.objects.create_user(email=email, password="x" * 16, full_name=name)
    return RiderProfile.objects.create(
        user=user, vehicle_type=VehicleType.values[0], is_on_shift=on_shift
    )


# ── Reject reasons (KDS-D) ────────────────────────────────────────────────────


def test_the_queue_lists_the_reject_reasons(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    body = kitchen.get(reverse("v1:kds:queue")).json()
    assert [r["code"] for r in body["reject_reasons"]] == list(REJECT_REASONS)
    assert all(r["title"] for r in body["reject_reasons"])


def test_a_rejection_needs_a_reason_from_the_list(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    url = reverse(
        "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "reject"}
    )
    for body in ({}, {"note": "just because"}, {"reason": "made-up"}):
        response = kitchen.post(url, body, format="json")
        assert response.status_code >= 400
    paid_order.refresh_from_db()
    assert paid_order.status == OrderStatus.PAID


def test_the_reason_is_recorded_for_the_customer(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    url = reverse(
        "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "reject"}
    )
    response = kitchen.post(url, {"reason": "too_busy", "note": "Back at 6pm"}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    event = paid_order.events.get(to_status=OrderStatus.REJECTED)
    assert event.note == f"{REJECT_REASONS['too_busy']}. Back at 6pm"


def test_accepting_needs_no_reason(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    url = reverse(
        "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "accept"}
    )
    assert kitchen.post(url, {}, format="json").json()["status"] == "confirmed"


# ── Riders ────────────────────────────────────────────────────────────────────


def test_riders_are_listed_on_shift_first(kitchen) -> None:  # type: ignore[no-untyped-def]
    rider("off@example.com", "Ade Off", on_shift=False)
    rider("on@example.com", "Bisi On", on_shift=True)
    riders = kitchen.get(reverse("v1:kds:riders")).json()["riders"]
    assert [(r["name"], r["is_on_shift"]) for r in riders] == [("Bisi", True), ("Ade", False)]


def test_an_assigned_rider_appears_on_the_ticket(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    profile = rider("on@example.com", "Bisi On", on_shift=True)
    kitchen.post(
        reverse("v1:kds:assign-rider", kwargs={"reference": paid_order.reference}),
        {"rider": str(profile.pk)},
        format="json",
    )
    ticket = kitchen.get(reverse("v1:kds:queue")).json()["orders"][0]
    assert ticket["rider"] == {"name": "Bisi"}


def test_a_ticket_without_a_rider_says_so(kitchen, paid_order) -> None:  # type: ignore[no-untyped-def]
    assert kitchen.get(reverse("v1:kds:queue")).json()["orders"][0]["rider"] is None


# ── 86 list (KDS-E) ───────────────────────────────────────────────────────────


def test_the_item_list_includes_sold_out_dishes(kitchen, branch, category) -> None:  # type: ignore[no-untyped-def]
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Jollof",
        slug="jollof",
        base_price=1,
        needs_repricing=False,
    )
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Suya",
        slug="suya",
        base_price=1,
        needs_repricing=False,
        is_available_now=False,
    )
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Unpriced",
        slug="unpriced",
        base_price=1,
        needs_repricing=True,
    )
    items = kitchen.get(reverse("v1:kds:items")).json()["items"]
    assert [(i["slug"], i["is_available_now"]) for i in items] == [
        ("jollof", True),
        ("suya", False),
    ]
    assert items[0]["category"] == category.name


def test_bringing_a_dish_back_shows_in_the_list(kitchen, branch, category) -> None:  # type: ignore[no-untyped-def]
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Suya",
        slug="suya",
        base_price=1,
        needs_repricing=False,
        is_available_now=False,
    )
    kitchen.post(
        reverse("v1:kds:availability", kwargs={"slug": "suya"}),
        {"is_available_now": True},
        format="json",
    )
    [item] = kitchen.get(reverse("v1:kds:items")).json()["items"]
    assert item["is_available_now"] is True


@pytest.mark.parametrize("name", ["v1:kds:riders", "v1:kds:items"])
def test_the_new_endpoints_are_kitchen_only(api_client, verified_user, name) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse(name)).status_code in (401, 403)
    api_client.force_authenticate(user=verified_user)
    assert api_client.get(reverse(name)).status_code == 403
