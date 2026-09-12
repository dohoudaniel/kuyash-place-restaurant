"""Cart API tests."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.carts.models import Cart, CartItem, CartStatus
from apps.catalog.models import MenuItem, Modifier, ModifierGroup, Variant

pytestmark = pytest.mark.django_db

CART = "v1:carts:cart"
ITEMS = "v1:carts:items"


@pytest.fixture
def burger(db, branch, category):  # type: ignore[no-untyped-def]
    return MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Classic Smash Burger",
        slug="classic-smash-burger",
        base_price=1_090_000,
        needs_repricing=False,
    )


def add(api_client, slug="classic-smash-burger", **extra):  # type: ignore[no-untyped-def]
    return api_client.post(
        reverse(ITEMS), {"menu_item": slug, "quantity": 1, **extra}, format="json"
    )


# ── Reading ───────────────────────────────────────────────────────────────────


def test_an_empty_cart_is_returned_not_404(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse(CART))
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["totals"]["grand_total"]["display"] == "₦0.00"


def test_a_guest_receives_a_cart_token(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    response = add(api_client)
    assert response.status_code == 201
    assert response["X-Cart-Token"]


def test_a_guest_cart_persists_across_requests(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    body = api_client.get(reverse(CART), HTTP_X_CART_TOKEN=token).json()
    assert len(body["items"]) == 1


def test_carts_are_not_shared_between_guests(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    add(api_client)
    body = api_client.get(reverse(CART), HTTP_X_CART_TOKEN="someone-elses-token").json()
    assert body["items"] == []


# ── The rule that matters ─────────────────────────────────────────────────────


def test_a_client_supplied_price_is_ignored(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    """The server is the only authority on money.

    The frontend computes every price in the browser today, so this is the most
    important assertion in the cart suite.
    """
    response = api_client.post(
        reverse(ITEMS),
        {
            "menu_item": "classic-smash-burger",
            "quantity": 1,
            "price": 1,
            "unit_price": 1,
            "line_subtotal": 1,
            "discount": 999_999,
            "total": 1,
        },
        format="json",
    )
    assert response.status_code == 201
    totals = response.json()["totals"]
    assert totals["grand_total"]["amount"] == 1_090_000
    assert totals["discount"]["amount"] == 0


def test_money_is_always_an_object_never_a_bare_number(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    body = add(api_client).json()
    for value in body["totals"].values():
        assert set(value) == {"amount", "currency", "display"}
        assert isinstance(value["amount"], int)


# ── Mutations ─────────────────────────────────────────────────────────────────


def test_adding_an_unavailable_item_is_refused(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    burger.is_available_now = False
    burger.save()
    response = add(api_client)
    assert response.status_code == 409
    assert response.json()["code"] == "item_unavailable"


def test_adding_a_placeholder_priced_item_is_refused(api_client, branch, unpriced_item) -> None:  # type: ignore[no-untyped-def]
    """Repricing gate: an unconfirmed price must not be purchasable."""
    response = add(api_client, slug=unpriced_item.slug)
    assert response.status_code == 409


def test_updating_quantity_reprices_the_line(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    item_id = api_client.get(reverse(CART), HTTP_X_CART_TOKEN=token).json()["items"][0]["id"]

    response = api_client.patch(
        reverse("v1:carts:item-detail", kwargs={"pk": item_id}),
        {"quantity": 3},
        format="json",
        HTTP_X_CART_TOKEN=token,
    )
    assert response.json()["totals"]["subtotal"]["amount"] == 3_270_000


def test_removing_a_line(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    item_id = api_client.get(reverse(CART), HTTP_X_CART_TOKEN=token).json()["items"][0]["id"]
    response = api_client.delete(
        reverse("v1:carts:item-detail", kwargs={"pk": item_id}), HTTP_X_CART_TOKEN=token
    )
    assert response.json()["items"] == []


def test_a_cart_line_cannot_be_touched_from_another_cart(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    item_id = api_client.get(reverse(CART), HTTP_X_CART_TOKEN=token).json()["items"][0]["id"]
    response = api_client.delete(
        reverse("v1:carts:item-detail", kwargs={"pk": item_id}),
        HTTP_X_CART_TOKEN="a-different-token",
    )
    assert response.status_code == 404


def test_emptying_the_cart(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    body = api_client.delete(reverse(CART), HTTP_X_CART_TOKEN=token).json()
    assert body["items"] == []


# ── Modifiers ─────────────────────────────────────────────────────────────────


def test_a_required_modifier_group_is_enforced(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    """The frontend's "Please select all required options" gate validates against
    a global mock array and is therefore meaningless."""
    ModifierGroup.objects.create(item=burger, name="Choose a flavour", min_select=1, max_select=1)
    response = add(api_client)
    assert response.status_code == 422
    assert "Choose at least 1" in response.json()["detail"]


def test_exceeding_max_select_is_refused(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    group = ModifierGroup.objects.create(item=burger, name="Extras", min_select=0, max_select=1)
    first = Modifier.objects.create(group=group, name="Cheese", price_delta=30_000)
    second = Modifier.objects.create(group=group, name="Bacon", price_delta=70_000)

    response = add(
        api_client,
        modifiers=[{"modifier": str(first.id)}, {"modifier": str(second.id)}],
    )
    assert response.status_code == 422
    assert "at most 1" in response.json()["detail"]


def test_a_modifier_from_another_item_is_refused(api_client, branch, category, burger) -> None:  # type: ignore[no-untyped-def]
    """Pancakes must not be orderable with the burger's extras."""
    pancakes = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Pancake Stack",
        slug="pancake-stack",
        base_price=950_000,
        needs_repricing=False,
    )
    group = ModifierGroup.objects.create(item=pancakes, name="Syrup", min_select=0, max_select=1)
    syrup = Modifier.objects.create(group=group, name="Maple", price_delta=20_000)

    response = add(api_client, modifiers=[{"modifier": str(syrup.id)}])
    assert response.status_code == 422
    assert "not an option" in response.json()["detail"]


def test_modifiers_change_the_price(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    group = ModifierGroup.objects.create(item=burger, name="Extras", min_select=0, max_select=3)
    cheese = Modifier.objects.create(group=group, name="Extra cheese", price_delta=30_000)

    body = add(api_client, modifiers=[{"modifier": str(cheese.id)}]).json()
    assert body["items"][0]["unit_price"]["amount"] == 1_120_000
    assert body["items"][0]["modifiers"][0]["price_delta"]["display"] == "₦300.00"


def test_a_variant_changes_the_price(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    triple = Variant.objects.create(item=burger, name="Triple", price_delta=300_000)
    body = add(api_client, variant=str(triple.id)).json()
    assert body["items"][0]["unit_price"]["amount"] == 1_390_000
    assert body["items"][0]["variant_name"] == "Triple"


# ── Promo ─────────────────────────────────────────────────────────────────────


def test_applying_a_promo_discounts_the_cart(api_client, branch, burger, promo) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    response = api_client.post(
        reverse("v1:carts:promo"), {"code": "WELCOME10"}, format="json", HTTP_X_CART_TOKEN=token
    )
    assert response.status_code == 200
    body = response.json()
    assert body["promo_code"] == "WELCOME10"
    assert body["totals"]["discount"]["amount"] == 109_000


def test_an_invalid_promo_is_reported_not_applied(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    response = api_client.post(
        reverse("v1:carts:promo"), {"code": "NOPE"}, format="json", HTTP_X_CART_TOKEN=token
    )
    assert response.status_code == 422
    assert response.json()["code"] == "promo_invalid"


def test_removing_a_promo(api_client, branch, burger, promo) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    api_client.post(
        reverse("v1:carts:promo"), {"code": "WELCOME10"}, format="json", HTTP_X_CART_TOKEN=token
    )
    body = api_client.delete(reverse("v1:carts:promo"), HTTP_X_CART_TOKEN=token).json()
    assert body["promo_code"] == ""
    assert body["totals"]["discount"]["amount"] == 0


def test_there_is_no_endpoint_listing_promo_codes() -> None:
    """The current cart UI enumerates every available code to the customer."""
    from django.urls import NoReverseMatch

    for name in ("v1:carts:promo-list", "v1:promotions:list", "v1:carts:promos"):
        with pytest.raises(NoReverseMatch):
            reverse(name)


# ── Fulfilment ────────────────────────────────────────────────────────────────


def test_setting_pickup_clears_the_delivery_fee(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    body = api_client.patch(
        reverse("v1:carts:fulfilment"),
        {"fulfilment_type": "pickup"},
        format="json",
        HTTP_X_CART_TOKEN=token,
    ).json()
    assert body["fulfilment_type"] == "pickup"
    assert body["totals"]["delivery_fee"]["amount"] == 0


def test_setting_a_tip(api_client, branch, burger) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    body = api_client.patch(
        reverse("v1:carts:fulfilment"),
        {"fulfilment_type": "pickup", "tip": 50_000},
        format="json",
        HTTP_X_CART_TOKEN=token,
    ).json()
    assert body["totals"]["tip"]["display"] == "₦500.00"


def test_a_guest_cannot_use_a_saved_address(api_client, branch, burger, address) -> None:  # type: ignore[no-untyped-def]
    token = add(api_client)["X-Cart-Token"]
    response = api_client.patch(
        reverse("v1:carts:fulfilment"),
        {"delivery_address": str(address.id)},
        format="json",
        HTTP_X_CART_TOKEN=token,
    )
    assert response.status_code == 422


def test_a_user_cannot_use_someone_elses_address(  # type: ignore[no-untyped-def]
    api_client, branch, burger, address, db
) -> None:
    from apps.accounts.models import User

    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-staple-xyz"
    )
    api_client.force_authenticate(user=intruder)
    add(api_client)
    response = api_client.patch(
        reverse("v1:carts:fulfilment"), {"delivery_address": str(address.id)}, format="json"
    )
    assert response.status_code == 422


# ── Merge on login ────────────────────────────────────────────────────────────


def test_a_guest_cart_merges_into_the_user_cart(  # type: ignore[no-untyped-def]
    api_client, branch, burger, verified_user
) -> None:
    token = add(api_client)["X-Cart-Token"]

    api_client.force_authenticate(user=verified_user)
    response = api_client.post(reverse("v1:carts:merge"), HTTP_X_CART_TOKEN=token)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    guest = Cart.objects.get(session_token=token)
    assert guest.status == CartStatus.ABANDONED
    assert CartItem.objects.filter(cart__user=verified_user).count() == 1


def test_merging_keeps_items_already_in_the_user_cart(  # type: ignore[no-untyped-def]
    api_client, branch, burger, verified_user
) -> None:
    token = add(api_client)["X-Cart-Token"]

    api_client.force_authenticate(user=verified_user)
    add(api_client)  # a line added while signed in
    body = api_client.post(reverse("v1:carts:merge"), HTTP_X_CART_TOKEN=token).json()
    assert len(body["items"]) == 2


def test_merge_requires_authentication(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    assert api_client.post(reverse("v1:carts:merge")).status_code in (401, 403)


def test_a_signed_in_user_gets_one_cart_per_branch(  # type: ignore[no-untyped-def]
    api_client, branch, burger, verified_user
) -> None:
    api_client.force_authenticate(user=verified_user)
    add(api_client)
    add(api_client)
    assert Cart.objects.filter(user=verified_user, status=CartStatus.ACTIVE).count() == 1
