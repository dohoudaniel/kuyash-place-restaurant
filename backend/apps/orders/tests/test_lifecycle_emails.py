"""Order lifecycle emails.

Which transitions write to a customer, and what those messages contain.
"""

from __future__ import annotations

import pytest

from apps.notifications.models import Notification
from apps.orders.models import OrderStatus
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


def sent_keys() -> set[str]:
    return set(Notification.objects.values_list("template_key", flat=True))


def body_of(key: str) -> str:
    return Notification.objects.get(template_key=key).body


def test_payment_confirms_to_the_customer(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, OrderStatus.PAID)

    assert "order_confirmation" in sent_keys()
    body = body_of("order_confirmation")
    assert order.reference in body
    assert "₦21,800.00" in body
    assert "Ada" in body


def test_a_delivery_confirmation_names_the_address(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, OrderStatus.PAID)
    assert "12 Adeola Odeku Street" in body_of("order_confirmation")


def test_a_pickup_confirmation_says_collection(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.models import FulfilmentType

    ready_cart.fulfilment_type = FulfilmentType.PICKUP
    ready_cart.delivery_address = None
    ready_cart.save()

    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, OrderStatus.PAID)
    assert "collection" in body_of("order_confirmation").lower()


def test_the_full_delivery_journey_writes_four_emails(ready_cart, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ):
        transition(order, status)

    assert sent_keys() == {
        "order_confirmation",
        "order_accepted",
        "order_out_for_delivery",
        "order_delivered",
    }


def test_a_pickup_order_is_told_when_it_is_ready(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """'Ready' matters for collection; for delivery it is an internal step."""
    from apps.carts.models import FulfilmentType

    ready_cart.fulfilment_type = FulfilmentType.PICKUP
    ready_cart.delivery_address = None
    ready_cart.save()

    order = place_order(cart=ready_cart, payment_method="card")
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ):
        transition(order, status)

    assert "order_ready" in sent_keys()


def test_a_delivery_order_is_not_emailed_at_ready(ready_cart) -> None:
    order = place_order(cart=ready_cart, payment_method="card")
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ):
        transition(order, status)
    assert "order_ready" not in sent_keys()


def test_the_dispatch_email_names_the_rider(ready_cart, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User
    from apps.delivery.models import DeliveryAssignment, RiderProfile

    order = place_order(cart=ready_cart, payment_method="card")
    rider_user = User.objects.create_user(
        email="emeka@kuyashplace.com",
        password="correct-horse-battery-staple",
        full_name="Emeka Rider",
        phone="+2348099887766",
    )
    DeliveryAssignment.objects.create(
        order=order, rider=RiderProfile.objects.create(user=rider_user)
    )
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
    ):
        transition(order, status)

    body = body_of("order_out_for_delivery")
    assert "Emeka" in body
    assert "+2348099887766" in body


def test_a_rejection_tells_a_paid_customer_about_the_refund(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, OrderStatus.PAID)
    transition(order, OrderStatus.REJECTED)
    assert "refunded in full" in body_of("order_rejected")


def test_a_cancellation_tells_an_unpaid_customer_they_were_not_charged(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Cash orders start confirmed and unpaid, so cancelling one must reassure
    rather than promise a refund that was never taken."""
    order = place_order(cart=ready_cart, payment_method="cash")
    transition(order, OrderStatus.CANCELLED)
    assert "not been charged" in body_of("order_cancelled")


def test_a_guest_order_emails_the_guest_address(branch, category, cart, zone) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.models import FulfilmentType
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem

    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    svc.add_item(cart=cart, item_slug="burger")
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    order = place_order(
        cart=cart,
        payment_method="card",
        guest={"email": "guest@example.com", "phone": "+2348012345678", "full_name": "Guest"},
    )
    transition(order, OrderStatus.PAID)

    assert Notification.objects.get(template_key="order_confirmation").recipient == (
        "guest@example.com"
    )


def test_internal_transitions_do_not_email(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Confirmed is a kitchen step; the customer hears at 'preparing'."""
    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, OrderStatus.PAID)
    Notification.objects.all().delete()

    transition(order, OrderStatus.CONFIRMED)
    assert not Notification.objects.exists()
