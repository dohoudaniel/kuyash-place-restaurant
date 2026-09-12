"""Cart service edge cases."""

from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from apps.carts.models import Cart, CartItem, CartStatus, FulfilmentType
from apps.carts.services import cart as svc
from apps.carts.services.cart import CartValidationError
from apps.carts.services.pricing import price_cart
from apps.catalog.models import (
    AvailabilityWindow,
    MenuItem,
    Modifier,
    ModifierGroup,
    Variant,
)
from apps.common.exceptions import ItemUnavailable
from apps.core.models import Weekday

pytestmark = pytest.mark.django_db


@pytest.fixture
def burger(db, branch, category):  # type: ignore[no-untyped-def]
    return MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )


def test_zero_quantity_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CartValidationError, match="at least 1"):
        svc.add_item(cart=cart, item_slug="burger", quantity=0)


def test_an_unknown_item_is_refused(cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ItemUnavailable, match="not on the menu"):
        svc.add_item(cart=cart, item_slug="does-not-exist")


def test_an_unknown_variant_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    import uuid

    with pytest.raises(CartValidationError, match="size or portion"):
        svc.add_item(cart=cart, item_slug="burger", variant_id=str(uuid.uuid4()))


def test_an_inactive_variant_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    variant = Variant.objects.create(item=burger, name="Retired", price_delta=0, is_active=False)
    with pytest.raises(CartValidationError):
        svc.add_item(cart=cart, item_slug="burger", variant_id=str(variant.id))


def test_an_unknown_modifier_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    import uuid

    with pytest.raises(CartValidationError, match="do not exist"):
        svc.add_item(cart=cart, item_slug="burger", modifiers=[{"modifier": str(uuid.uuid4())}])


def test_an_unavailable_modifier_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    group = ModifierGroup.objects.create(item=burger, name="Extras", max_select=2)
    modifier = Modifier.objects.create(
        group=group, name="Truffle", price_delta=100_000, is_available=False
    )
    with pytest.raises(ItemUnavailable, match="Truffle"):
        svc.add_item(cart=cart, item_slug="burger", modifiers=[{"modifier": str(modifier.id)}])


def test_updating_to_zero_quantity_is_refused(cart, burger) -> None:  # type: ignore[no-untyped-def]
    line = svc.add_item(cart=cart, item_slug="burger")
    with pytest.raises(CartValidationError, match="Remove the line"):
        svc.update_item(item=line, quantity=0)


def test_updating_instructions(cart, burger) -> None:  # type: ignore[no-untyped-def]
    line = svc.add_item(cart=cart, item_slug="burger")
    svc.update_item(item=line, instructions="  no onions  ")
    line.refresh_from_db()
    assert line.special_instructions == "no onions"


def test_an_invalid_fulfilment_type_is_refused(cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CartValidationError, match="delivery or pickup"):
        svc.set_fulfilment(cart=cart, fulfilment_type="teleport")


def test_a_negative_tip_is_refused(cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CartValidationError, match="cannot be negative"):
        svc.set_fulfilment(cart=cart, tip=-100)


def test_switching_to_pickup_clears_the_address(user_cart, address) -> None:  # type: ignore[no-untyped-def]
    svc.set_fulfilment(cart=user_cart, address_id=str(address.id))
    assert user_cart.delivery_address == address

    svc.set_fulfilment(cart=user_cart, fulfilment_type=FulfilmentType.PICKUP)
    user_cart.refresh_from_db()
    assert user_cart.delivery_address is None


def test_merging_a_cart_into_itself_is_a_no_op(user_cart) -> None:  # type: ignore[no-untyped-def]
    assert svc.merge_carts(guest_cart=user_cart, user_cart=user_cart) == user_cart
    user_cart.refresh_from_db()
    assert user_cart.status == CartStatus.ACTIVE


def test_merging_carries_the_promo_and_tip_over(branch, verified_user, promo) -> None:  # type: ignore[no-untyped-def]
    guest = Cart.objects.create(branch=branch, promo_code=promo, tip=50_000)
    mine = Cart.objects.create(branch=branch, user=verified_user)

    svc.merge_carts(guest_cart=guest, user_cart=mine)
    mine.refresh_from_db()
    assert mine.promo_code == promo
    assert mine.tip == 50_000


def test_merging_does_not_overwrite_an_existing_promo(branch, verified_user, promo) -> None:  # type: ignore[no-untyped-def]
    from apps.promotions.models import DiscountType, PromoCode

    mine_promo = PromoCode.objects.create(
        branch=branch, code="MINE", discount_type=DiscountType.FIXED, value=1
    )
    guest = Cart.objects.create(branch=branch, promo_code=promo)
    mine = Cart.objects.create(branch=branch, user=verified_user, promo_code=mine_promo)

    svc.merge_carts(guest_cart=guest, user_cart=mine)
    mine.refresh_from_db()
    assert mine.promo_code == mine_promo


def test_clearing_removes_items_promo_and_tip(user_cart, burger, promo) -> None:  # type: ignore[no-untyped-def]
    svc.add_item(cart=user_cart, item_slug="burger")
    user_cart.promo_code = promo
    user_cart.tip = 50_000
    user_cart.save()

    svc.clear(cart=user_cart)
    user_cart.refresh_from_db()
    assert user_cart.is_empty
    assert user_cart.promo_code is None
    assert user_cart.tip == 0


def test_a_withdrawn_item_in_a_cart_is_reported(cart, burger) -> None:  # type: ignore[no-untyped-def]
    """An item pulled from the menu while it sat in someone's cart."""
    svc.add_item(cart=cart, item_slug="burger")
    burger.is_active = False
    burger.save()

    priced = price_cart(cart)
    assert priced.unavailable[0]["reason"] == "withdrawn"


def test_an_item_outside_its_serving_hours_is_reported(cart, burger) -> None:  # type: ignore[no-untyped-def]
    svc.add_item(cart=cart, item_slug="burger")
    now = timezone.localtime()
    start = (now + dt.timedelta(hours=2)).time()
    end = (now + dt.timedelta(hours=3)).time()
    if start > end:  # pragma: no cover - only around midnight
        pytest.skip("window would wrap past midnight")
    for weekday in Weekday.values:
        AvailabilityWindow.objects.create(
            item=burger, weekday=weekday, starts_at=start, ends_at=end
        )

    priced = price_cart(cart)
    assert priced.unavailable[0]["reason"] == "outside_serving_hours"


def test_a_targeted_promo_only_discounts_matching_lines(  # type: ignore[no-untyped-def]
    branch, category, user_cart, promo, address, burger
) -> None:
    """A category-targeted code must not discount the rest of the basket."""
    from apps.catalog.models import Category

    drinks = Category.objects.create(branch=branch, name="Drinks", slug="drinks")
    cola = MenuItem.objects.create(
        branch=branch,
        category=drinks,
        name="Cola",
        slug="cola",
        base_price=500_000,
        needs_repricing=False,
    )
    svc.add_item(cart=user_cart, item_slug="burger")  # ₦10,000 — not targeted
    svc.add_item(cart=user_cart, item_slug="cola")  # ₦5,000  — targeted

    promo.applicable_categories.add(drinks)
    user_cart.promo_code = promo
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.subtotal == 1_500_000
    assert priced.discount_total == 50_000  # 10% of the ₦5,000 cola only
    assert cola.slug in {line.slug for line in priced.lines}


def test_an_item_only_promo_targets_that_item(  # type: ignore[no-untyped-def]
    branch, category, user_cart, promo, address, burger
) -> None:
    other = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Wrap",
        slug="wrap",
        base_price=500_000,
        needs_repricing=False,
    )
    svc.add_item(cart=user_cart, item_slug="burger")
    svc.add_item(cart=user_cart, item_slug="wrap")

    promo.applicable_items.add(other)
    user_cart.promo_code = promo
    user_cart.delivery_address = address
    user_cart.save()

    assert price_cart(user_cart).discount_total == 50_000


def test_an_invalid_promo_attached_to_a_cart_is_simply_not_applied(  # type: ignore[no-untyped-def]
    cart, burger, promo
) -> None:
    """A code whose conditions stop holding must quietly stop discounting rather
    than keep granting money."""
    svc.add_item(cart=cart, item_slug="burger")
    cart.promo_code = promo
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()
    assert price_cart(cart).discount_total == 100_000

    promo.min_order_value = 99_000_000  # now unreachable
    promo.save()
    cart.refresh_from_db()

    priced = price_cart(cart)
    assert priced.discount_total == 0
    assert priced.promo_code == ""


def test_cart_string_representations(cart, user_cart, burger) -> None:  # type: ignore[no-untyped-def]
    line = svc.add_item(cart=cart, item_slug="burger", quantity=2)
    assert "guest:" in str(cart)
    assert "ada@example.com" in str(user_cart)
    assert str(line) == "2× Burger"
    assert CartItem.objects.filter(cart=cart).exists()
