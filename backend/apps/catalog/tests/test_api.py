"""Catalogue API tests."""

from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import AvailabilityWindow, DietaryTag, MenuItem, Modifier, ModifierGroup
from apps.core.models import Weekday

pytestmark = pytest.mark.django_db


def items_url() -> str:
    return reverse("v1:catalog:items")


def test_list_returns_orderable_items(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(items_url()).json()
    assert [row["slug"] for row in body["results"]] == [menu_item.slug]


def test_placeholder_priced_items_are_hidden(  # type: ignore[no-untyped-def]
    api_client, menu_item: MenuItem, unpriced_item: MenuItem
) -> None:
    """The single most important rule in Phase 1A.

    An item whose price is an unconfirmed placeholder must never be purchasable,
    and the surest way is for customers never to see it.
    """
    slugs = [row["slug"] for row in api_client.get(items_url()).json()["results"]]
    assert menu_item.slug in slugs
    assert unpriced_item.slug not in slugs


def test_placeholder_item_detail_is_404(api_client, unpriced_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    url = reverse("v1:catalog:item-detail", kwargs={"slug": unpriced_item.slug})
    assert api_client.get(url).status_code == 404


def test_prices_are_money_objects_not_numbers(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    row = api_client.get(items_url()).json()["results"][0]
    assert row["price"] == {
        "amount": 1_090_000,
        "currency": "NGN",
        "display": "₦10,900.00",
    }


def test_detail_exposes_variants_and_per_item_modifiers(  # type: ignore[no-untyped-def]
    api_client, menu_item: MenuItem
) -> None:
    group = ModifierGroup.objects.create(
        item=menu_item, name="Add extras", min_select=0, max_select=3
    )
    Modifier.objects.create(group=group, name="Extra cheese", price_delta=15_000)

    url = reverse("v1:catalog:item-detail", kwargs={"slug": menu_item.slug})
    body = api_client.get(url).json()

    assert body["modifier_groups"][0]["name"] == "Add extras"
    assert body["modifier_groups"][0]["is_required"] is False
    modifier = body["modifier_groups"][0]["modifiers"][0]
    assert modifier["price_delta"]["display"] == "₦150.00"


def test_filter_by_category(api_client, menu_item: MenuItem, branch, category) -> None:  # type: ignore[no-untyped-def]
    from apps.catalog.models import Category

    other = Category.objects.create(branch=branch, name="Desserts", slug="desserts")
    MenuItem.objects.create(
        branch=branch,
        category=other,
        name="Cheesecake",
        slug="cheesecake",
        base_price=850_000,
        needs_repricing=False,
    )
    body = api_client.get(items_url(), {"category": "desserts"}).json()
    assert [row["slug"] for row in body["results"]] == ["cheesecake"]


def test_search_matches_name_and_description(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(items_url(), {"search": "smash"}).json()["results"]
    assert api_client.get(items_url(), {"search": "pickles"}).json()["results"]
    assert not api_client.get(items_url(), {"search": "zzzznothing"}).json()["results"]


def test_filter_by_price_range(api_client, menu_item: MenuItem, branch, category) -> None:  # type: ignore[no-untyped-def]
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Cheap Side",
        slug="cheap-side",
        base_price=100_000,
        needs_repricing=False,
    )
    body = api_client.get(items_url(), {"max_price": 200_000}).json()
    assert [row["slug"] for row in body["results"]] == ["cheap-side"]


def test_dietary_filter_uses_and_semantics(
    api_client, menu_item: MenuItem, branch, category
) -> None:  # type: ignore[no-untyped-def]
    """ "vegan,gluten-free" means both, not either."""
    vegan = DietaryTag.objects.create(name="Vegan", slug="vegan")
    gf = DietaryTag.objects.create(name="Gluten free", slug="gluten-free")

    both = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Both",
        slug="both",
        base_price=500_000,
        needs_repricing=False,
    )
    both.dietary_tags.set([vegan, gf])
    menu_item.dietary_tags.set([vegan])

    body = api_client.get(items_url(), {"dietary": "vegan,gluten-free"}).json()
    assert [row["slug"] for row in body["results"]] == ["both"]


def test_sort_by_price(api_client, menu_item: MenuItem, branch, category) -> None:  # type: ignore[no-untyped-def]
    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Cheap",
        slug="cheap",
        base_price=100_000,
        needs_repricing=False,
    )
    asc = [r["slug"] for r in api_client.get(items_url(), {"sort": "price_asc"}).json()["results"]]
    desc = [
        r["slug"] for r in api_client.get(items_url(), {"sort": "price_desc"}).json()["results"]
    ]
    assert asc == ["cheap", menu_item.slug]
    assert desc == [menu_item.slug, "cheap"]


def test_sort_by_rating_puts_unrated_last(
    api_client, menu_item: MenuItem, branch, category
) -> None:  # type: ignore[no-untyped-def]
    """An unrated dish belongs below a 3-star one, not above a 5-star one.

    The frontend's rating sort is `return 0`.
    """
    from decimal import Decimal

    menu_item.average_rating = Decimal("3.0")
    menu_item.save()
    top = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Top",
        slug="top",
        base_price=500_000,
        needs_repricing=False,
        average_rating=Decimal("5.0"),
    )
    unrated = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Unrated",
        slug="unrated",
        base_price=500_000,
        needs_repricing=False,
    )
    order = [r["slug"] for r in api_client.get(items_url(), {"sort": "rating"}).json()["results"]]
    assert order == [top.slug, menu_item.slug, unrated.slug]


def test_sort_by_popular_uses_real_order_counts(
    api_client, menu_item: MenuItem, branch, category
) -> None:  # type: ignore[no-untyped-def]
    popular = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Popular",
        slug="popular",
        base_price=500_000,
        needs_repricing=False,
        order_count=99,
    )
    order = [r["slug"] for r in api_client.get(items_url(), {"sort": "popular"}).json()["results"]]
    assert order[0] == popular.slug


def test_available_only_honours_time_windows(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    """A breakfast-only item disappears outside its window."""
    now = timezone.localtime()
    for weekday in Weekday.values:
        AvailabilityWindow.objects.create(
            item=menu_item,
            weekday=weekday,
            starts_at=dt.time(3, 0),
            ends_at=dt.time(3, 30),
        )
    if dt.time(3, 0) <= now.time() <= dt.time(3, 30):  # pragma: no cover - clock-dependent
        pytest.skip("test clock sits inside the window")

    assert not api_client.get(items_url(), {"available_only": "true"}).json()["results"]
    assert api_client.get(items_url()).json()["results"]  # still listed without the filter


def test_eighty_sixed_item_is_flagged_but_still_listed(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    menu_item.is_available_now = False
    menu_item.save()
    row = api_client.get(items_url()).json()["results"][0]
    assert row["is_available"] is False


def test_categories_report_orderable_counts(  # type: ignore[no-untyped-def]
    api_client, menu_item: MenuItem, unpriced_item: MenuItem
) -> None:
    body = api_client.get(reverse("v1:catalog:categories")).json()
    assert body[0]["slug"] == "burgers"
    assert body[0]["item_count"] == 1  # the placeholder-priced one is not counted


def test_featured_endpoint(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    menu_item.is_featured = True
    menu_item.save()
    body = api_client.get(reverse("v1:catalog:featured")).json()
    assert [row["slug"] for row in body] == [menu_item.slug]


def test_dietary_tag_vocabulary(api_client, db) -> None:  # type: ignore[no-untyped-def]
    DietaryTag.objects.create(name="Vegan", slug="vegan", display_order=1)
    body = api_client.get(reverse("v1:catalog:dietary-tags")).json()
    assert body[0]["slug"] == "vegan"


def test_malformed_numeric_filters_are_ignored_not_fatal(api_client, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(items_url(), {"min_price": "abc", "min_rating": "xyz"})
    assert response.status_code == 200
    assert response.json()["results"]
