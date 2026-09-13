"""Order placement.

Replaces `app/checkout/page.tsx`, which generates an id from Date.now(),
clears the cart, and persists nothing.
"""

from __future__ import annotations

import pytest

from apps.carts.models import CartStatus
from apps.common.exceptions import BranchClosed, ItemUnavailable, PriceChanged
from apps.orders.models import Order, OrderStatus, PaymentStatus
from apps.orders.services.placement import CheckoutBlocked, place_order
from apps.orders.services.state import transition
from apps.promotions.models import PromoRedemption, RedemptionStatus

pytestmark = pytest.mark.django_db


def place(cart, **kwargs):  # type: ignore[no-untyped-def]
    return place_order(cart=cart, payment_method=kwargs.pop("payment_method", "card"), **kwargs)


def test_placing_an_order_snapshots_the_lines(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    line = order.items.get()
    assert line.name_snapshot == "Classic Smash Burger"
    assert line.unit_price == 1_090_000
    assert line.quantity == 2
    assert order.subtotal == 2_180_000


def test_the_snapshot_survives_a_later_price_change(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Raising a price must not rewrite what a customer already agreed to pay."""
    from apps.catalog.models import MenuItem

    order = place(ready_cart)
    original = order.grand_total

    item = MenuItem.objects.get(slug="classic-smash-burger")
    item.base_price = 9_999_000
    item.save()

    order.refresh_from_db()
    assert order.grand_total == original
    assert order.items.get().unit_price == 1_090_000


def test_the_address_is_copied_not_referenced(ready_cart, address) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    assert order.street == "12 Adeola Odeku Street"
    assert order.delivery_zone_name == "Victoria Island"

    address.street = "Somewhere else entirely"
    address.save()
    order.refresh_from_db()
    assert order.street == "12 Adeola Odeku Street"


def test_references_are_random_and_unique(ready_cart, branch, category) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.models import generate_reference

    references = {generate_reference() for _ in range(500)}
    assert len(references) == 500
    assert all(ref.startswith("KYS-") and len(ref) == 10 for ref in references)
    # No ambiguous characters: an order reference gets read aloud on the phone.
    assert not any(set("01OI") & set(ref[4:]) for ref in references)


def test_card_orders_await_payment(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart, payment_method="card")
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.payment_status == PaymentStatus.PENDING


def test_cash_orders_are_confirmed_immediately(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart, payment_method="cash")
    assert order.status == OrderStatus.CONFIRMED
    assert order.payment_status == PaymentStatus.UNPAID


def test_the_cart_is_not_cleared_until_payment(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """ORD-4. The frontend clears the cart before anything is persisted, so a
    failed payment loses the basket with no way back."""
    order = place(ready_cart)
    ready_cart.refresh_from_db()
    assert ready_cart.status == CartStatus.CONVERTED
    assert ready_cart.items.exists()  # still there

    transition(order, OrderStatus.PAID)
    ready_cart.refresh_from_db()
    assert not ready_cart.items.exists()  # cleared only now


def test_the_price_changed_guard_refuses_a_mismatch(ready_cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PriceChanged) as excinfo:
        place(ready_cart, expected_total=1)
    assert excinfo.value.extra["actual"]["amount"] == 2_180_000
    assert not Order.objects.exists()


def test_a_matching_expected_total_is_accepted(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services.pricing import price_cart

    total = price_cart(ready_cart).grand_total
    assert place(ready_cart, expected_total=total).grand_total == total


def test_an_empty_cart_cannot_be_ordered(user_cart, address) -> None:  # type: ignore[no-untyped-def]
    user_cart.delivery_address = address
    user_cart.save()
    with pytest.raises(CheckoutBlocked, match="empty"):
        place(user_cart)


def test_a_sold_out_item_blocks_placement(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.catalog.models import MenuItem

    item = MenuItem.objects.get(slug="classic-smash-burger")
    item.is_available_now = False
    item.save()

    with pytest.raises(ItemUnavailable):
        place(ready_cart)
    assert not Order.objects.exists()


def test_a_closed_branch_blocks_placement(ready_cart, branch) -> None:  # type: ignore[no-untyped-def]
    branch.is_accepting_orders = False
    branch.save()
    with pytest.raises(BranchClosed):
        place(ready_cart)


def test_an_undeliverable_address_blocks_placement(ready_cart, verified_user) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import Address

    ready_cart.delivery_address = Address.objects.create(
        user=verified_user,
        label="other",
        recipient_name="Ada",
        phone="+2348012345678",
        street="5 Aso Drive",
        area="Maitama",
        city="Abuja",
        state="FCT",
    )
    ready_cart.save()
    with pytest.raises(CheckoutBlocked):
        place(ready_cart)


def test_a_guest_order_requires_an_email(branch, category, cart, zone) -> None:  # type: ignore[no-untyped-def]
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

    with pytest.raises(CheckoutBlocked, match="email"):
        place(cart)

    order = place(cart, guest={"email": "guest@example.com", "phone": "+2348012345678"})
    assert order.guest_email == "guest@example.com"
    assert order.guest_token


def test_an_eta_is_calculated(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    assert order.estimated_ready_at is not None
    assert order.estimated_delivery_at > order.estimated_ready_at


def test_a_promo_creates_a_pending_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)

    redemption = PromoRedemption.objects.get(order=order)
    assert redemption.status == RedemptionStatus.PENDING
    assert redemption.discount_amount == order.discount_total
    assert order.promo_code_snapshot == "WELCOME10"


def test_payment_confirms_the_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)

    transition(order, OrderStatus.PAID)
    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.CONFIRMED


def test_cancelling_reverses_the_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    """RF-4: a customer gets their promo use back."""
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)
    transition(order, OrderStatus.PAID)

    transition(order, OrderStatus.CANCELLED)
    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.REVERSED
    assert promo.times_used == 0  # the allowance is free again


def test_payment_queues_a_confirmation_email(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.notifications.models import Notification

    order = place(ready_cart)
    transition(order, OrderStatus.PAID)
    assert Notification.objects.filter(
        template_key="order_confirmation", recipient="ada@example.com"
    ).exists()


def test_delivery_increments_popularity(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """So "sort by popular" reflects real sales rather than a placeholder."""
    from apps.catalog.models import MenuItem

    order = place(ready_cart)
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ):
        transition(order, status)

    assert MenuItem.objects.get(slug="classic-smash-burger").order_count == 2


def test_payment_marks_the_amount_paid(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    transition(order, OrderStatus.PAID)
    order.refresh_from_db()
    assert order.payment_status == PaymentStatus.PAID
    assert order.amount_paid == order.grand_total


def test_a_transfer_order_is_refused_when_there_is_no_account_to_pay_into(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Hiding the option is not enough: the API itself refuses."""
    from apps.orders.services.placement import CheckoutBlocked

    with pytest.raises(CheckoutBlocked):
        place(ready_cart, payment_method="transfer")


def test_a_transfer_order_is_accepted_once_bank_details_exist(ready_cart) -> None:  # type: ignore[no-untyped-def]
    branch = ready_cart.branch
    branch.bank_name = "Example Bank"
    branch.bank_account_name = "Kuyash Place Ltd"
    branch.bank_account_number = "0123456789"
    branch.save()

    order = place(ready_cart, payment_method="transfer")

    assert order.payment_method == "transfer"
    assert order.status == "pending_payment"
