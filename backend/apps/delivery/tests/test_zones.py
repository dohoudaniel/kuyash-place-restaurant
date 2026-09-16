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


# ── The indexed mirror ────────────────────────────────────────────────────────


def test_area_names_are_mirrored_into_the_indexed_table(zone: DeliveryZone) -> None:
    from apps.delivery.models import DeliveryArea

    assert set(DeliveryArea.objects.filter(zone=zone).values_list("normalised", flat=True)) == {
        "victoria island",
        "vi",
        "eko atlantic",
    }


def test_editing_the_json_list_keeps_the_mirror_in_step(zone: DeliveryZone) -> None:
    """Staff carry on editing `areas` in the admin; nothing about that changed."""
    from apps.delivery.models import DeliveryArea

    zone.areas = ["Ikoyi", "Banana Island"]
    zone.save()

    assert set(DeliveryArea.objects.filter(zone=zone).values_list("normalised", flat=True)) == {
        "ikoyi",
        "banana island",
    }
    assert resolve_zone(zone.branch, area="Banana Island") == zone
    assert resolve_zone(zone.branch, area="Victoria Island") is None


def test_resolution_is_one_query_however_many_zones(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    """It used to load every active zone and substring-match in Python, on every
    address save and every checkout price."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def cost() -> int:
        with CaptureQueriesContext(connection) as captured:
            resolve_zone(branch, street="12 Adeola Odeku, Victoria Island", city="Lagos")
        return len(captured)

    small = cost()
    for index in range(20):
        DeliveryZone.objects.create(
            branch=branch,
            name=f"Zone {index}",
            slug=f"zone-{index}",
            fee=100_000,
            min_order_value=0,
            areas=[f"Area {index}", f"Alias {index}"],
            display_order=50 + index,
        )
    assert cost() == small == 1


def test_punctuation_and_case_do_not_stop_a_match(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    assert resolve_zone(branch, area="victoria-island!") == zone
    assert resolve_zone(branch, street="Plot 4, EKO ATLANTIC.") == zone


def test_an_area_name_no_longer_matches_inside_another_word(branch, zone: DeliveryZone) -> None:  # type: ignore[no-untyped-def]
    """The one behavioural change, and it is a fix.

    Matching was raw substring, so the alias "VI" matched inside "Divine" and a
    Divine Street address in Ikeja was quietly resolved to Victoria Island — and
    charged its delivery fee. Candidates are now whole words.
    """
    assert resolve_zone(branch, street="10 Divine Street", city="Ikeja") is None
    assert resolve_zone(branch, area="VI", city="Lagos") == zone
