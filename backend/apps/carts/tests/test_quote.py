"""Item quotes and the typed cart response.

The item dialog shows a live total while options are chosen. The quote must be
the figure the cart will charge — so it is computed by the same service, and the
test that matters most here checks the two agree.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.carts.models import Cart
from apps.catalog.models import AvailabilityWindow, MenuItem, Modifier, ModifierGroup, Variant

pytestmark = pytest.mark.django_db


@pytest.fixture
def configurable(menu_item: MenuItem) -> SimpleNamespace:
    large = Variant.objects.create(item=menu_item, name="Large", price_delta=200_000)
    group = ModifierGroup.objects.create(item=menu_item, name="Extras", min_select=0, max_select=2)
    cheese = Modifier.objects.create(group=group, name="Extra cheese", price_delta=50_000)
    bacon = Modifier.objects.create(group=group, name="Bacon", price_delta=80_000)
    return SimpleNamespace(item=menu_item, large=large, group=group, cheese=cheese, bacon=bacon)


def quote(client, **body):  # type: ignore[no-untyped-def]
    return client.post(reverse("v1:carts:quote"), body, format="json")


def full_config(c: SimpleNamespace, quantity: int = 2) -> dict:  # type: ignore[type-arg]
    return {
        "menu_item": c.item.slug,
        "quantity": quantity,
        "variant": str(c.large.id),
        "modifiers": [{"modifier": str(c.cheese.id)}, {"modifier": str(c.bacon.id)}],
    }


def test_a_quote_prices_the_whole_configuration(api_client, configurable) -> None:  # type: ignore[no-untyped-def]
    response = quote(api_client, **full_config(configurable))

    assert response.status_code == 200
    body = response.json()
    # ₦10,900 base + ₦2,000 large + ₦500 cheese + ₦800 bacon = ₦14,200 each
    assert body["unit_price"]["amount"] == 1_420_000
    assert body["line_total"]["amount"] == 2_840_000
    assert body["line_total"]["display"] == "₦28,400.00"
    assert body["is_available_now"] is True


def test_the_quote_is_what_the_cart_then_charges(api_client, configurable) -> None:  # type: ignore[no-untyped-def]
    config = full_config(configurable, quantity=1)
    quoted = quote(api_client, **config).json()

    cart = api_client.post(reverse("v1:carts:items"), config, format="json").json()

    assert cart["items"][0]["unit_price"] == quoted["unit_price"]


def test_quoting_creates_no_cart(api_client, configurable) -> None:  # type: ignore[no-untyped-def]
    before = Cart.objects.count()
    response = quote(api_client, **full_config(configurable))
    assert Cart.objects.count() == before
    assert "X-Cart-Token" not in response


def test_a_missing_required_choice_is_refused(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    group = ModifierGroup.objects.create(
        item=menu_item, name="Doneness", min_select=1, max_select=1
    )
    Modifier.objects.create(group=group, name="Medium", price_delta=0)

    response = quote(api_client, menu_item=menu_item.slug)

    assert response.status_code == 422
    assert response.json()["code"] == "cart_invalid"


def test_an_option_from_another_dish_is_refused(api_client, configurable, category, branch) -> None:  # type: ignore[no-untyped-def]
    other = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Fries",
        slug="fries",
        base_price=300_000,
        needs_repricing=False,
    )
    foreign = Modifier.objects.create(
        group=ModifierGroup.objects.create(item=other, name="Salt", max_select=1), name="Extra salt"
    )

    response = quote(
        api_client, menu_item=configurable.item.slug, modifiers=[{"modifier": str(foreign.id)}]
    )

    assert response.status_code == 422


def test_an_unpriced_dish_cannot_be_quoted(api_client, unpriced_item) -> None:  # type: ignore[no-untyped-def]
    response = quote(api_client, menu_item=unpriced_item.slug)
    assert response.status_code == 409
    assert response.json()["code"] == "item_unavailable"


def test_a_dish_outside_its_window_is_quoted_but_flagged(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    """Reading the breakfast menu at dinner still shows prices."""
    today = timezone.localtime().weekday()
    for weekday in (day for day in range(7) if day != today):
        AvailabilityWindow.objects.create(
            item=menu_item, weekday=weekday, starts_at=dt.time(0, 0), ends_at=dt.time(23, 59)
        )

    response = quote(api_client, menu_item=menu_item.slug)

    assert response.status_code == 200
    assert response.json()["is_available_now"] is False


def test_a_modifier_choice_must_be_a_uuid(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:carts:items"),
        {"menu_item": menu_item.slug, "modifiers": [{"modifier": "not-a-uuid"}]},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_the_cart_reports_its_item_count(api_client, configurable) -> None:  # type: ignore[no-untyped-def]
    body = api_client.post(
        reverse("v1:carts:items"),
        {"menu_item": configurable.item.slug, "quantity": 3},
        format="json",
    ).json()
    assert body["item_count"] == 3
    assert body["items"][0]["menu_item"]["slug"] == configurable.item.slug
    assert body["prices_include_vat"] is True
