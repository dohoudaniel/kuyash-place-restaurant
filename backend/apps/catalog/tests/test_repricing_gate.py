"""The repricing deployment gate.

This is the mechanism that makes launching with ₦14.90 burgers impossible
rather than merely inadvisable. See docs/DECISIONS.md ADR-008.
"""

from __future__ import annotations

import pytest

from apps.catalog.checks import check_no_unpriced_items
from apps.catalog.models import MenuItem

pytestmark = pytest.mark.django_db


def test_gate_passes_when_every_price_is_confirmed(menu_item: MenuItem) -> None:
    assert check_no_unpriced_items(None) == []


def test_gate_fails_while_placeholders_remain(unpriced_item: MenuItem) -> None:
    errors = check_no_unpriced_items(None)
    assert len(errors) == 1
    assert errors[0].id == "kuyash.E001"
    assert unpriced_item.slug in errors[0].hint


def test_gate_ignores_inactive_items(unpriced_item: MenuItem) -> None:
    """An unpublished draft should not block a deploy."""
    unpriced_item.is_active = False
    unpriced_item.save()
    assert check_no_unpriced_items(None) == []


def test_gate_truncates_a_long_list(branch, category) -> None:  # type: ignore[no-untyped-def]
    for index in range(25):
        MenuItem.objects.create(
            branch=branch,
            category=category,
            name=f"Item {index}",
            slug=f"item-{index}",
            base_price=1000,
            needs_repricing=True,
        )
    hint = check_no_unpriced_items(None)[0].hint
    assert "25 total" in hint


def test_seeded_catalogue_blocks_deployment(branch) -> None:  # type: ignore[no-untyped-def]
    """Seeding must not produce a shippable system.

    Every one of the 18 seeded prices is a dollar figure carried over from the
    frontend. If this test ever passes with zero errors, the seed data has
    silently become "real" and the safety net is gone.
    """
    from apps.catalog.seed import seed_catalogue

    seed_catalogue(branch)
    errors = check_no_unpriced_items(None)
    assert len(errors) == 1
    assert "18 active menu item(s)" in errors[0].msg


def test_options_are_hidden_while_the_item_needs_repricing(  # type: ignore[no-untyped-def]
    api_client, unpriced_item
) -> None:
    """Variants and modifiers have no flag of their own — the item's covers them.

    Otherwise an item could be repriced correctly while its "Extra cheese"
    still carried a placeholder price.
    """
    from django.urls import reverse

    from apps.catalog.models import Modifier, ModifierGroup, Variant

    Variant.objects.create(item=unpriced_item, name="Large", price_delta=100_000)
    group = ModifierGroup.objects.create(item=unpriced_item, name="Extras", max_select=2)
    Modifier.objects.create(group=group, name="Extra cheese", price_delta=30_000)

    url = reverse("v1:catalog:item-detail", kwargs={"slug": unpriced_item.slug})
    assert api_client.get(url).status_code == 404

    listing = api_client.get(reverse("v1:catalog:items")).json()
    assert unpriced_item.slug not in [row["slug"] for row in listing["results"]]


def test_seeded_option_prices_are_naira_scale(branch) -> None:  # type: ignore[no-untyped-def]
    """Guard against the kobo/naira slip that produced ₦1.50 extra cheese.

    Any non-zero option price below ₦10.00 is almost certainly a value entered
    in naira into a kobo field.
    """
    from apps.catalog.models import Modifier, Variant
    from apps.catalog.seed import seed_catalogue

    seed_catalogue(branch)

    suspicious = [
        (modifier.name, modifier.price_delta)
        for modifier in Modifier.objects.exclude(price_delta=0)
        if abs(modifier.price_delta) < 1_000
    ] + [
        (variant.name, variant.price_delta)
        for variant in Variant.objects.exclude(price_delta=0)
        if abs(variant.price_delta) < 1_000
    ]
    assert not suspicious, f"option prices look like naira entered into a kobo field: {suspicious}"
