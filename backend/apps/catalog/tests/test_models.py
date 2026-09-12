"""Catalogue model behaviour."""

from __future__ import annotations

import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.models import AvailabilityWindow, MenuItem, Modifier, ModifierGroup, Variant
from apps.core.models import Weekday

pytestmark = pytest.mark.django_db


def test_priced_item_is_orderable(menu_item: MenuItem) -> None:
    assert menu_item.is_orderable is True
    assert menu_item.available_at() is True


def test_placeholder_priced_item_is_not_orderable(unpriced_item: MenuItem) -> None:
    """The repricing flag is the gate, not a label."""
    assert unpriced_item.is_orderable is False
    assert unpriced_item.available_at() is False


def test_publishing_stamps_published_at(menu_item: MenuItem) -> None:
    assert menu_item.published_at is not None


def test_placeholder_item_is_never_published(unpriced_item: MenuItem) -> None:
    """'Newest' must not surface something customers cannot buy."""
    assert unpriced_item.published_at is None


def test_eighty_sixing_an_item_makes_it_unavailable(menu_item: MenuItem) -> None:
    menu_item.is_available_now = False
    menu_item.save()
    assert menu_item.available_at() is False
    assert menu_item.is_orderable is True  # still published, just out of stock


def test_item_with_no_windows_is_always_available(menu_item: MenuItem) -> None:
    assert menu_item.availability_windows.count() == 0
    assert menu_item.available_at() is True


def test_availability_window_restricts_to_its_hours(menu_item: MenuItem) -> None:
    """Breakfast should not be orderable at 21:00."""
    for weekday in Weekday.values:
        AvailabilityWindow.objects.create(
            item=menu_item, weekday=weekday, starts_at=dt.time(7, 0), ends_at=dt.time(11, 30)
        )
    tz = timezone.get_current_timezone()
    breakfast = dt.datetime(2026, 9, 14, 9, 0, tzinfo=tz)
    dinner = dt.datetime(2026, 9, 14, 21, 0, tzinfo=tz)
    assert menu_item.available_at(breakfast) is True
    assert menu_item.available_at(dinner) is False


def test_window_must_end_after_it_starts(menu_item: MenuItem) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        AvailabilityWindow.objects.create(
            item=menu_item, weekday=0, starts_at=dt.time(11, 0), ends_at=dt.time(7, 0)
        )


def test_effective_prep_time_falls_back_to_the_branch(menu_item: MenuItem) -> None:
    menu_item.prep_time_minutes = None
    menu_item.save()
    assert menu_item.effective_prep_minutes == menu_item.branch.default_prep_minutes


def test_only_one_default_variant_per_item(menu_item: MenuItem) -> None:
    Variant.objects.create(item=menu_item, name="Double", price_delta=0, is_default=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        Variant.objects.create(item=menu_item, name="Triple", price_delta=350, is_default=True)


def test_variant_price_delta_may_be_negative(menu_item: MenuItem) -> None:
    """A smaller portion legitimately costs less."""
    variant = Variant.objects.create(item=menu_item, name="Single", price_delta=-20_000)
    assert variant.price_delta == -20_000


def test_modifier_group_rejects_max_below_min(menu_item: MenuItem) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        ModifierGroup.objects.create(item=menu_item, name="Broken", min_select=3, max_select=1)


def test_required_group_is_derived_from_min_select(menu_item: MenuItem) -> None:
    optional = ModifierGroup.objects.create(
        item=menu_item, name="Extras", min_select=0, max_select=3
    )
    required = ModifierGroup.objects.create(
        item=menu_item, name="Flavour", min_select=1, max_select=1
    )
    assert optional.is_required is False
    assert required.is_required is True


def test_modifiers_belong_to_one_item_only(menu_item: MenuItem, category) -> None:  # type: ignore[no-untyped-def]
    """Per-item groups: pancakes must not be offered extra cheese.

    The frontend renders one global MOCK_CUSTOMIZATIONS array on every dish.
    """
    pancakes = MenuItem.objects.create(
        branch=menu_item.branch,
        category=category,
        name="Pancake Stack",
        slug="pancake-stack",
        base_price=950_000,
        needs_repricing=False,
    )
    group = ModifierGroup.objects.create(item=menu_item, name="Add extras", max_select=3)
    Modifier.objects.create(group=group, name="Extra cheese", price_delta=15_000)

    assert menu_item.modifier_groups.count() == 1
    assert pancakes.modifier_groups.count() == 0


def test_slug_is_unique_per_branch(menu_item: MenuItem, category) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(IntegrityError), transaction.atomic():
        MenuItem.objects.create(
            branch=menu_item.branch,
            category=category,
            name="Duplicate",
            slug=menu_item.slug,
            base_price=100_000,
        )


def test_orderable_queryset_excludes_placeholders(
    menu_item: MenuItem, unpriced_item: MenuItem
) -> None:
    slugs = set(MenuItem.objects.orderable().values_list("slug", flat=True))
    assert menu_item.slug in slugs
    assert unpriced_item.slug not in slugs
