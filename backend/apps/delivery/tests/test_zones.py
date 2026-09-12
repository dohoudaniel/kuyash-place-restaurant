"""Delivery zone resolution."""

from __future__ import annotations

import pytest

from apps.delivery.models import DeliveryZone
from apps.delivery.selectors import resolve_zone

pytestmark = pytest.mark.django_db


def test_resolves_by_area_name(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    assert resolve_zone(branch, area="Victoria Island", city="Lagos") == zone


def test_matching_is_case_insensitive(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    assert resolve_zone(branch, area="victoria island", city="lagos") == zone


def test_resolves_from_an_alias(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    assert resolve_zone(branch, area="VI", city="Lagos") == zone


def test_resolves_from_the_street_line(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    """Customers often put the district in the street field."""
    assert resolve_zone(branch, street="12 Adeola Odeku, Victoria Island", city="Lagos") == zone


def test_unknown_area_resolves_to_none(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    """None is a real answer: the address is outside the delivery area."""
    assert resolve_zone(branch, area="Abuja", city="Abuja") is None


def test_empty_address_resolves_to_none(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    assert resolve_zone(branch) is None


def test_inactive_zones_are_ignored(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    zone.is_active = False
    zone.save()
    assert resolve_zone(branch, area="Victoria Island") is None


def test_first_matching_zone_wins_by_display_order(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    DeliveryZone.objects.create(
        branch=branch,
        name="Island Wide",
        slug="island-wide",
        fee=300_000,
        min_order_value=200_000,
        areas=["Victoria Island"],
        display_order=99,
    )
    assert resolve_zone(branch, area="Victoria Island") == zone


def test_zone_fee_is_kobo(zone: DeliveryZone) -> None:
    """₦1,500.00, not ₦1.50 — the delivery fee is where this slip is costliest."""
    from apps.common.money import format_money

    assert format_money(zone.fee) == "₦1,500.00"
