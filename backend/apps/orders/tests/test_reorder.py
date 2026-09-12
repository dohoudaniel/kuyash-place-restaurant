"""Reorder: a fresh quote for the same request, not a copy of an old one.

`OrderHistorySection.tsx` pushes stored line objects straight back into the cart
store — old prices, dishes that may have left the menu, options that may no
longer exist. These tests pin the behaviour that replaces it.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.carts.models import Cart
from apps.catalog.models import MenuItem, Modifier, ModifierGroup, Variant
from apps.orders.services.placement import place_order
from apps.orders.services.reorder import CartNotEmpty, reorder

pytestmark = pytest.mark.django_db


@pytest.fixture
def past_order(ready_cart):  # type: ignore[no-untyped-def]
    return place_order(cart=ready_cart, payment_method="card")


@pytest.fixture
def empty_cart(db, branch, verified_user) -> Cart:  # type: ignore[no-untyped-def]
    return Cart.objects.create(branch=branch, user=verified_user)


def burger() -> MenuItem:
    return MenuItem.objects.get(slug="classic-smash-burger")


# ──────────────────────────────────────────────────────────────────────────────
# The happy path
# ──────────────────────────────────────────────────────────────────────────────


def test_reorder_rebuilds_the_lines(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    result = reorder(order=past_order, cart=empty_cart)
    line = empty_cart.items.get()
    assert line.menu_item == burger()
    assert line.quantity == 2
    assert result.is_complete
    assert result.changes == []


def test_reorder_carries_the_special_instructions(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    past_order.items.update(special_instructions="No pickles.")
    reorder(order=past_order, cart=empty_cart)
    assert empty_cart.items.get().special_instructions == "No pickles."


# ──────────────────────────────────────────────────────────────────────────────
# Revalidation — the whole point
# ──────────────────────────────────────────────────────────────────────────────


def test_a_price_rise_is_charged_and_reported(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """The line goes back at today's price, and the customer is told."""
    item = burger()
    item.base_price = 1_290_000
    item.save(update_fields=["base_price"])

    result = reorder(order=past_order, cart=empty_cart)

    assert empty_cart.items.get().unit_price_snapshot == 1_290_000
    change = result.changes[0]
    assert change["type"] == "price_increased"
    assert change["old"]["amount"] == 1_090_000
    assert change["new"]["amount"] == 1_290_000
    assert change["new"]["display"] == "₦12,900.00"


def test_a_price_cut_is_reported_too(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    item = burger()
    item.base_price = 900_000
    item.save(update_fields=["base_price"])
    result = reorder(order=past_order, cart=empty_cart)
    assert result.changes[0]["type"] == "price_reduced"


def test_a_delisted_dish_is_skipped_not_silently_dropped(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    item = burger()
    item.is_active = False
    item.save(update_fields=["is_active"])

    result = reorder(order=past_order, cart=empty_cart)

    assert empty_cart.items.count() == 0
    assert result.unavailable[0]["name"] == "Classic Smash Burger"
    assert "no longer on the menu" in result.unavailable[0]["reason"]
    assert result.is_complete is False
    assert result.added_nothing is True


def test_an_unpriced_dish_cannot_come_back(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """The repricing gate applies to reorder as much as to the menu."""
    item = burger()
    item.needs_repricing = True
    item.save(update_fields=["needs_repricing"])
    result = reorder(order=past_order, cart=empty_cart)
    assert result.added_nothing is True


def test_a_dish_outside_its_serving_window_is_skipped(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """A breakfast item reordered at dinner. It is on the menu, just not now."""
    import datetime as dt

    from django.utils import timezone

    from apps.catalog.models import AvailabilityWindow

    # Windows on every day except today, so the result does not depend on the
    # clock — the branch fixture is open around the clock for the same reason.
    today = timezone.localtime().weekday()
    for weekday in (day for day in range(7) if day != today):
        AvailabilityWindow.objects.create(
            item=burger(), weekday=weekday, starts_at=dt.time(0, 0), ends_at=dt.time(23, 59)
        )

    result = reorder(order=past_order, cart=empty_cart)
    assert result.added_nothing is True
    assert "unavailable right now" in result.unavailable[0]["reason"]


def test_a_sold_out_dish_is_skipped(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """`is_available_now=False` takes it out of the orderable queryset entirely."""
    item = burger()
    item.is_available_now = False
    item.save(update_fields=["is_available_now"])
    result = reorder(order=past_order, cart=empty_cart)
    assert result.added_nothing is True


def test_a_dish_deleted_and_recreated_is_matched_by_slug(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """The foreign key is nulled on delete; the slug snapshot is what survives."""
    line = past_order.items.get()
    line.menu_item = None
    line.save(update_fields=["menu_item"])

    result = reorder(order=past_order, cart=empty_cart)
    assert result.added
    assert empty_cart.items.get().menu_item == burger()


def test_a_line_with_no_resolvable_item_is_reported(past_order, empty_cart) -> None:  # type: ignore[no-untyped-def]
    line = past_order.items.get()
    line.menu_item = None
    line.slug_snapshot = ""
    line.save(update_fields=["menu_item", "slug_snapshot"])

    result = reorder(order=past_order, cart=empty_cart)
    assert result.added_nothing is True
    assert result.unavailable[0]["name"] == "Classic Smash Burger"


# ──────────────────────────────────────────────────────────────────────────────
# Variants and modifiers, which order lines hold only by name
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def order_with_options(ready_cart, branch):  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc

    item = burger()
    Variant.objects.create(item=item, name="Large", price_delta=200_000)
    group = ModifierGroup.objects.create(item=item, name="Extras", min_select=0, max_select=3)
    Modifier.objects.create(group=group, name="Extra cheese", price_delta=50_000)

    ready_cart.items.all().delete()
    variant = Variant.objects.get(item=item, name="Large")
    modifier = Modifier.objects.get(name="Extra cheese")
    svc.add_item(
        cart=ready_cart,
        item_slug=item.slug,
        quantity=1,
        variant_id=str(variant.id),
        modifiers=[{"modifier": str(modifier.id), "quantity": 1}],
    )
    return place_order(cart=ready_cart, payment_method="card")


def test_a_variant_is_re_resolved_by_name(order_with_options, empty_cart) -> None:  # type: ignore[no-untyped-def]
    result = reorder(order=order_with_options, cart=empty_cart)
    line = empty_cart.items.get()
    assert line.variant.name == "Large"
    assert line.unit_price_snapshot == 1_090_000 + 200_000 + 50_000
    assert result.changes == []


def test_a_withdrawn_size_skips_the_line(order_with_options, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """Falling back to the base size would charge for something else."""
    Variant.objects.filter(name="Large").update(is_active=False)
    result = reorder(order=order_with_options, cart=empty_cart)
    assert result.added_nothing is True
    assert "“Large” is no longer offered" in result.unavailable[0]["reason"]


def test_a_withdrawn_optional_extra_is_dropped_and_reported(order_with_options, empty_cart) -> None:  # type: ignore[no-untyped-def]
    Modifier.objects.filter(name="Extra cheese").update(is_available=False)

    result = reorder(order=order_with_options, cart=empty_cart)

    line = empty_cart.items.get()
    assert line.modifiers.count() == 0
    assert line.unit_price_snapshot == 1_090_000 + 200_000
    change = next(c for c in result.changes if c["type"] == "options_removed")
    assert "Extra cheese" in change["detail"]


def test_a_withdrawn_required_option_skips_the_line(order_with_options, empty_cart) -> None:  # type: ignore[no-untyped-def]
    """A group that must have a choice, with nothing left to choose."""
    ModifierGroup.objects.filter(name="Extras").update(min_select=1, max_select=1)
    Modifier.objects.filter(name="Extra cheese").update(is_available=False)

    result = reorder(order=order_with_options, cart=empty_cart)

    assert result.added_nothing is True
    assert result.unavailable[0]["name"] == "Classic Smash Burger"


# ──────────────────────────────────────────────────────────────────────────────
# The existing basket
# ──────────────────────────────────────────────────────────────────────────────


def test_reorder_refuses_to_overwrite_a_basket(past_order, ready_cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CartNotEmpty):
        reorder(order=past_order, cart=ready_cart)


def test_reorder_replaces_when_told_to(past_order, ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc

    svc.add_item(cart=ready_cart, item_slug="classic-smash-burger", quantity=5)
    before = ready_cart.items.count()

    result = reorder(order=past_order, cart=ready_cart, replace=True)

    assert result.replaced_lines == before
    assert ready_cart.items.count() == 1
    assert ready_cart.items.get().quantity == 2


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────


def test_endpoint_rebuilds_the_basket(api_client, verified_user, past_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))
    assert response.status_code == 200
    assert response.data["added"] == 1
    assert response.data["cart"]["items"]


def test_endpoint_reports_a_price_change(api_client, verified_user, past_order) -> None:  # type: ignore[no-untyped-def]
    item = burger()
    item.base_price = 1_290_000
    item.save(update_fields=["base_price"])

    api_client.force_authenticate(verified_user)
    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))
    assert response.data["changes"][0]["type"] == "price_increased"


def current_cart(user, branch) -> Cart:  # type: ignore[no-untyped-def]
    """The basket the endpoint will resolve.

    Not `ready_cart`: placing an order closes that one, so the caller's live
    basket afterwards is a different row.
    """
    from apps.carts.services import cart as svc

    return svc.resolve_cart(branch=branch, user=user)


def test_endpoint_409s_rather_than_discarding_a_basket(
    api_client, verified_user, past_order, branch
) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc

    svc.add_item(
        cart=current_cart(verified_user, branch), item_slug="classic-smash-burger", quantity=1
    )
    api_client.force_authenticate(verified_user)

    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))

    assert response.status_code == 409
    assert response.data["code"] == "cart_not_empty"


def test_endpoint_replaces_on_confirmation(api_client, verified_user, past_order, branch) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc

    svc.add_item(
        cart=current_cart(verified_user, branch), item_slug="classic-smash-burger", quantity=4
    )
    api_client.force_authenticate(verified_user)
    response = api_client.post(
        reverse("v1:orders:reorder", args=[past_order.reference]), {"replace": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data["replaced_lines"] >= 1


def test_endpoint_explains_an_empty_result(api_client, verified_user, past_order) -> None:  # type: ignore[no-untyped-def]
    MenuItem.objects.filter(slug="classic-smash-burger").update(is_active=False)
    api_client.force_authenticate(verified_user)

    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))

    assert response.data["added"] == 0
    assert response.data["message"] == "Nothing from that order is available right now."


def test_endpoint_warns_when_only_some_lines_came_back(
    api_client, verified_user, past_order, ready_cart, category, branch
) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc

    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Jollof Rice",
        slug="jollof-rice",
        base_price=500_000,
        needs_repricing=False,
    )
    ready_cart.items.all().delete()
    svc.add_item(cart=ready_cart, item_slug="classic-smash-burger", quantity=1)
    svc.add_item(cart=ready_cart, item_slug="jollof-rice", quantity=1)
    order = place_order(cart=ready_cart, payment_method="card")
    MenuItem.objects.filter(slug="jollof-rice").update(is_active=False)

    api_client.force_authenticate(verified_user)
    response = api_client.post(reverse("v1:orders:reorder", args=[order.reference]))

    assert response.data["added"] == 1
    assert "Check your basket before paying" in response.data["message"]


def test_endpoint_requires_sign_in(api_client, past_order) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))
    assert response.status_code in {401, 403}


def test_you_cannot_reorder_somebody_elses_order(api_client, past_order, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    intruder = User.objects.create_user(email="mal@example.com", password="x" * 20)
    api_client.force_authenticate(intruder)

    response = api_client.post(reverse("v1:orders:reorder", args=[past_order.reference]))

    # 404, not 403: whether that reference exists is not disclosed.
    assert response.status_code == 404
