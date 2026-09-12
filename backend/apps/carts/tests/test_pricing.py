"""Pricing engine tests.

This module carries the same weight as the money tests: every path here can
change what a customer is charged.
"""

from __future__ import annotations

import pytest

from apps.carts.models import Cart, CartItem, CartItemModifier, FulfilmentType
from apps.carts.services.pricing import (
    compute_unit_price,
    compute_vat_for_lines,
    price_cart,
)
from apps.catalog.models import MenuItem, Modifier, ModifierGroup, TaxClass, Variant

pytestmark = pytest.mark.django_db


def add_line(cart: Cart, item: MenuItem, quantity: int = 1, variant=None) -> CartItem:  # type: ignore[no-untyped-def]
    return CartItem.objects.create(
        cart=cart,
        menu_item=item,
        quantity=quantity,
        variant=variant,
        unit_price_snapshot=item.base_price,
    )


# ── Pure arithmetic ───────────────────────────────────────────────────────────


def test_unit_price_sums_base_variant_and_modifiers() -> None:
    assert compute_unit_price(1_490_000, 300_000, [30_000, 20_000]) == 1_840_000


def test_unit_price_handles_a_negative_variant_delta() -> None:
    """A smaller portion legitimately costs less."""
    assert compute_unit_price(1_090_000, -150_000, []) == 940_000


def test_unit_price_never_goes_negative() -> None:
    assert compute_unit_price(100_000, -500_000, []) == 0


def test_vat_skips_zero_rated_and_exempt_lines() -> None:
    """The reason VAT cannot be computed from an order subtotal: a subtotal has
    no tax class, so a zero-rated item would be taxed through it."""
    lines = [
        (1_000_000, TaxClass.STANDARD),
        (1_000_000, TaxClass.ZERO_RATED),
        (1_000_000, TaxClass.EXEMPT),
    ]
    only_standard = compute_vat_for_lines(lines, rate_bps=750, inclusive=True)
    all_of_it = compute_vat_for_lines(
        [(3_000_000, TaxClass.STANDARD)], rate_bps=750, inclusive=True
    )
    assert only_standard == 69_767
    assert all_of_it == 209_302
    assert only_standard != all_of_it


# ── The documented worked example ─────────────────────────────────────────────


def test_matches_the_worked_example_in_the_payments_doc(  # type: ignore[no-untyped-def]
    branch, category, user_cart, promo, address
) -> None:
    """Reproduces docs/PAYMENTS.md §7.1 exactly.

    If this drifts, either the engine or the documentation is wrong.
    """
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Signature Grill Plate",
        slug="signature-grill-plate",
        base_price=1_490_000,
        needs_repricing=False,
    )
    large = Variant.objects.create(item=item, name="Large", price_delta=300_000)
    group = ModifierGroup.objects.create(item=item, name="Extras", max_select=3)
    extra = Modifier.objects.create(group=group, name="Extra sauce", price_delta=50_000)

    line = CartItem.objects.create(
        cart=user_cart,
        menu_item=item,
        variant=large,
        quantity=2,
        unit_price_snapshot=1_840_000,
    )
    CartItemModifier.objects.create(cart_item=line, modifier=extra)

    user_cart.promo_code = promo
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)

    assert priced.lines[0].unit_price == 1_840_000
    assert priced.subtotal == 3_680_000
    assert priced.discount_total == 368_000
    assert priced.delivery_fee == 0  # over the free-delivery threshold
    assert priced.grand_total == 3_312_000
    assert priced.vat_total == 231_070  # 3,312,000 × 7.5 / 107.5, ROUND_HALF_UP
    assert "included in the prices shown" in priced.vat_note


# ── VAT direction ─────────────────────────────────────────────────────────────


def test_vat_inclusive_does_not_add_to_the_total(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    """The customer pays the menu price. No surprise at checkout — which is what
    the published terms already promise."""
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_075_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    priced = price_cart(cart)
    assert priced.grand_total == 1_075_000
    assert priced.vat_total == 75_000


def test_vat_exclusive_adds_to_the_total(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    branch.prices_include_vat = False
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    priced = price_cart(cart)
    assert priced.vat_total == 75_000
    assert priced.grand_total == 1_075_000
    assert "added at checkout" in priced.vat_note


def test_zero_rated_item_attracts_no_vat(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Bread",
        slug="bread",
        base_price=1_000_000,
        needs_repricing=False,
        tax_class=TaxClass.ZERO_RATED,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    assert price_cart(cart).vat_total == 0


# ── Discount allocation ───────────────────────────────────────────────────────


def test_discount_is_allocated_across_lines_and_sums_exactly(  # type: ignore[no-untyped-def]
    branch, category, user_cart, promo, address
) -> None:
    """Allocation happens before VAT so each line is taxed on what it costs.

    The parts must sum exactly to the discount — no kobo lost or invented.
    """
    for index, price in enumerate((333_333, 333_333, 333_334)):
        item = MenuItem.objects.create(
            branch=branch,
            category=category,
            name=f"Item {index}",
            slug=f"item-{index}",
            base_price=price,
            needs_repricing=False,
        )
        add_line(user_cart, item)

    user_cart.promo_code = promo
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.subtotal == 1_000_000
    assert priced.discount_total == 100_000
    assert sum(line.discount for line in priced.lines) == priced.discount_total
    assert sum(line.line_after_discount for line in priced.lines) == 900_000


def test_percentage_discount_respects_its_cap(branch, category, user_cart, promo, address) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Feast",
        slug="feast",
        base_price=10_000_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.promo_code = promo
    user_cart.delivery_address = address
    user_cart.save()

    assert price_cart(user_cart).discount_total == 500_000  # capped, not ₦100,000


# ── Delivery ──────────────────────────────────────────────────────────────────


def test_delivery_fee_comes_from_the_zone(branch, category, user_cart, address) -> None:  # type: ignore[no-untyped-def]
    branch.free_delivery_threshold = None
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=500_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.delivery_fee == 150_000  # ₦1,500.00, not the hardcoded ₦5.00
    assert priced.estimated_minutes == 35


def test_free_delivery_over_the_threshold(branch, category, user_cart, address) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Feast",
        slug="feast",
        base_price=2_000_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.delivery_fee == 0
    assert "Free delivery" in priced.delivery_note


def test_pickup_has_no_delivery_fee(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=500_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    priced = price_cart(cart)
    assert priced.delivery_fee == 0
    assert "Collection" in priced.delivery_note


def test_delivery_without_an_address_blocks_checkout(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=500_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    priced = price_cart(cart)
    assert priced.can_checkout is False
    assert any(blocker["code"] == "address_required" for blocker in priced.blockers)


def test_address_outside_the_delivery_area_blocks_checkout(  # type: ignore[no-untyped-def]
    branch, category, user_cart, verified_user
) -> None:
    from apps.accounts.models import Address

    far = Address.objects.create(
        user=verified_user,
        label="other",
        recipient_name="Ada",
        phone="+2348012345678",
        street="5 Aso Drive",
        area="Maitama",
        city="Abuja",
        state="FCT",
    )
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=500_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.delivery_address = far
    user_cart.save()

    priced = price_cart(user_cart)
    assert any(blocker["code"] == "outside_delivery_area" for blocker in priced.blockers)


# ── Change detection ──────────────────────────────────────────────────────────


def test_a_price_rise_is_reported_not_silently_charged(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    """A state the current UI cannot even detect."""
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    item.base_price = 1_200_000
    item.save()

    priced = price_cart(cart)
    assert priced.lines[0].unit_price == 1_200_000  # charged at the live price
    assert priced.changes[0]["type"] == "price_increased"
    assert priced.changes[0]["old"]["display"] == "₦10,000.00"
    assert priced.changes[0]["new"]["display"] == "₦12,000.00"


def test_a_sold_out_item_blocks_checkout(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    item.is_available_now = False
    item.save()

    priced = price_cart(cart)
    assert priced.unavailable[0]["reason"] == "sold_out"
    assert priced.can_checkout is False


def test_an_empty_cart_cannot_check_out(cart) -> None:  # type: ignore[no-untyped-def]
    priced = price_cart(cart)
    assert priced.subtotal == 0
    assert priced.can_checkout is False
    assert any(blocker["code"] == "cart_empty" for blocker in priced.blockers)


def test_a_closed_branch_blocks_checkout(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    """Nothing currently stops a 3 a.m. order."""
    branch.is_accepting_orders = False
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    assert any(blocker["code"] == "branch_closed" for blocker in price_cart(cart).blockers)


# ── Tip and service charge ────────────────────────────────────────────────────


def test_a_tip_is_added_but_not_taxed(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_075_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.tip = 100_000
    cart.save()

    priced = price_cart(cart)
    assert priced.tip == 100_000
    assert priced.grand_total == 1_175_000
    assert priced.vat_total == 75_000  # unchanged by the tip


def test_service_charge_is_applied_and_taxed(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    branch.service_charge_bps = 500  # 5%
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    priced = price_cart(cart)
    assert priced.service_charge == 50_000
    assert priced.grand_total == 1_050_000


# ── Minimum-order and free-delivery-promo branches ────────────────────────────


def test_a_free_delivery_promo_waives_the_fee(branch, category, user_cart, address) -> None:  # type: ignore[no-untyped-def]
    """Distinct from the threshold waiver: the note must name the code."""
    from apps.promotions.models import DiscountType, PromoCode

    branch.free_delivery_threshold = None
    branch.save()
    code = PromoCode.objects.create(
        branch=branch,
        code="FREEDEL",
        discount_type=DiscountType.FREE_DELIVERY,
        min_order_value=0,
    )
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=500_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.promo_code = code
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.delivery_fee == 0
    assert priced.discount_total == 0  # free delivery discounts no goods
    assert "FREEDEL" in priced.delivery_note


def test_below_the_zone_minimum_blocks_checkout(branch, category, user_cart, address) -> None:  # type: ignore[no-untyped-def]
    """The zone minimum (₦2,000) is separate from the branch minimum."""
    branch.min_order_value = 0
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Side",
        slug="side",
        base_price=50_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    blockers = [b for b in priced.blockers if b["code"] == "below_minimum_order"]
    assert blockers
    assert "Victoria Island" in blockers[0]["detail"]


def test_below_the_branch_minimum_blocks_checkout(branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    branch.min_order_value = 500_000
    branch.save()
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Side",
        slug="side",
        base_price=50_000,
        needs_repricing=False,
    )
    add_line(cart, item)
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    priced = price_cart(cart)
    blockers = [b for b in priced.blockers if b["code"] == "below_minimum_order"]
    assert blockers
    assert "₦5,000.00" in blockers[0]["detail"]


def test_a_complete_cart_can_check_out(branch, category, user_cart, address) -> None:  # type: ignore[no-untyped-def]
    """The positive case, asserted explicitly.

    Without this the suite could go green with every cart permanently blocked —
    which is exactly what happened when the branch fixture was open only
    11:00–22:00 and the tests ran at night.
    """
    item = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    add_line(user_cart, item)
    user_cart.delivery_address = address
    user_cart.save()

    priced = price_cart(user_cart)
    assert priced.blockers == []
    assert priced.can_checkout is True
