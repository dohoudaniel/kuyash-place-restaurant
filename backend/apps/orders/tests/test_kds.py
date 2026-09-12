"""Kitchen Display System.

One screen the kitchen keeps open during service. Not the Django admin — a
misclick on a changelist should not cancel an order.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.catalog.models import MenuItem
from apps.orders.models import OrderStatus
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_order(ready_cart):  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    return transition(order, OrderStatus.PAID)


def test_the_queue_requires_kitchen_access(api_client, verified_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:kds:queue")).status_code in (401, 403)

    api_client.force_authenticate(user=verified_user)  # an ordinary customer
    assert api_client.get(reverse("v1:kds:queue")).status_code == 403


def test_the_queue_shows_live_tickets(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    body = api_client.get(reverse("v1:kds:queue")).json()

    ticket = body["orders"][0]
    assert ticket["reference"] == paid_order.reference
    assert ticket["elapsed_seconds"] >= 0
    assert ticket["is_late"] is False


def test_a_ticket_shows_what_the_kitchen_cooks_from(  # type: ignore[no-untyped-def]
    api_client, kitchen_user, ready_cart, branch, category
) -> None:
    """Modifiers and special instructions are first-class.

    They are exactly what the current frontend collects and then discards.
    """
    from apps.carts.services import cart as svc
    from apps.catalog.models import Modifier, ModifierGroup

    item = MenuItem.objects.get(slug="classic-smash-burger")
    group = ModifierGroup.objects.create(item=item, name="Extras", min_select=0, max_select=2)
    cheese = Modifier.objects.create(group=group, name="Extra cheese", price_delta=30_000)
    svc.add_item(
        cart=ready_cart,
        item_slug="classic-smash-burger",
        modifiers=[{"modifier": str(cheese.id)}],
        special_instructions="No pickles",
    )
    order = transition(place_order(cart=ready_cart, payment_method="card"), OrderStatus.PAID)

    api_client.force_authenticate(user=kitchen_user)
    tickets = api_client.get(reverse("v1:kds:queue")).json()["orders"]
    ticket = next(t for t in tickets if t["reference"] == order.reference)

    configured = next(line for line in ticket["items"] if line["modifiers"])
    assert configured["modifiers"] == ["Extra cheese"]
    assert configured["special_instructions"] == "No pickles"


def test_accepting_a_ticket(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse("v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "accept"})
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_advancing_a_ticket_through_service(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    url = reverse(
        "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "accept"}
    )
    api_client.post(url)

    advance = reverse(
        "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "advance"}
    )
    for target in ("preparing", "ready", "out_for_delivery", "delivered"):
        response = api_client.post(advance, {"to": target}, format="json")
        assert response.status_code == 200, target
        assert response.json()["status"] == target


def test_a_ticket_cannot_skip_states(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse(
            "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "advance"}
        ),
        {"to": "delivered"},
        format="json",
    )
    assert response.status_code == 409


def test_an_unknown_action_is_refused(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse(
            "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "teleport"}
        )
    )
    assert response.status_code == 400


def test_kitchen_cannot_refund_via_advance(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse(
            "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "advance"}
        ),
        {"to": "refunded"},
        format="json",
    )
    assert response.status_code == 400


def test_rejecting_a_ticket_notifies_the_customer(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    from apps.notifications.models import Notification

    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse(
            "v1:kds:transition", kwargs={"reference": paid_order.reference, "action": "reject"}
        ),
        {"note": "Out of beef"},
        format="json",
    )
    assert response.status_code == 200
    assert Notification.objects.filter(template_key="order_rejected").exists()


def test_eighty_sixing_an_item_hides_it_immediately(
    api_client, kitchen_user, branch, category
) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse("v1:kds:availability", kwargs={"slug": item.slug}),
        {"is_available_now": False},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["is_available_now"] is False

    api_client.force_authenticate(user=None)
    listing = api_client.get(reverse("v1:catalog:items"), {"available_only": "true"}).json()
    assert item.slug not in [row["slug"] for row in listing["results"]]


def test_assigning_a_rider(api_client, kitchen_user, paid_order, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User
    from apps.delivery.models import RiderProfile

    rider_user = User.objects.create_user(
        email="emeka@kuyashplace.com",
        password="correct-horse-battery-staple",
        full_name="Emeka Rider",
        phone="+2348099887766",
    )
    rider = RiderProfile.objects.create(user=rider_user, is_on_shift=True)

    api_client.force_authenticate(user=kitchen_user)
    response = api_client.post(
        reverse("v1:kds:assign-rider", kwargs={"reference": paid_order.reference}),
        {"rider": str(rider.pk)},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["rider"]["name"] == "Emeka"

    paid_order.refresh_from_db()
    assert paid_order.delivery_assignment.rider == rider


def test_the_rider_appears_on_the_customers_order(
    api_client, kitchen_user, paid_order, verified_user, db
) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User
    from apps.delivery.models import DeliveryAssignment, RiderProfile

    rider_user = User.objects.create_user(
        email="emeka@kuyashplace.com",
        password="correct-horse-battery-staple",
        full_name="Emeka Rider",
        phone="+2348099887766",
    )
    DeliveryAssignment.objects.create(
        order=paid_order, rider=RiderProfile.objects.create(user=rider_user)
    )

    api_client.force_authenticate(user=verified_user)
    body = api_client.get(
        reverse("v1:orders:detail", kwargs={"reference": paid_order.reference})
    ).json()
    assert body["rider"]["name"] == "Emeka"
    assert body["rider"]["phone"] == "+2348099887766"


def test_the_summary_reports_counts_and_revenue(api_client, kitchen_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=kitchen_user)
    transition(paid_order, OrderStatus.CONFIRMED, actor=kitchen_user)

    body = api_client.get(reverse("v1:kds:summary")).json()
    assert body["open_tickets"] >= 1
    assert set(body["todays_revenue"]) == {"amount", "currency", "display"}


def test_cash_orders_are_flagged_for_collection(api_client, kitchen_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    """The rider has to collect; the ticket must say so."""
    order = place_order(cart=ready_cart, payment_method="cash")
    api_client.force_authenticate(user=kitchen_user)
    tickets = api_client.get(reverse("v1:kds:queue")).json()["orders"]
    ticket = next(t for t in tickets if t["reference"] == order.reference)
    assert ticket["requires_cash_collection"] is True
    assert ticket["payment_status"] == "unpaid"
