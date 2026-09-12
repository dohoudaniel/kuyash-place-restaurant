"""Zone resolution."""

from __future__ import annotations

from apps.core.models import Branch
from apps.delivery.models import DeliveryZone


def resolve_zone(
    branch: Branch, *, city: str = "", area: str = "", street: str = ""
) -> DeliveryZone | None:
    """Find the delivery zone covering an address, or ``None``.

    ``None`` is a meaningful answer, not a failure: it means the address is
    outside the delivery area, and the UI must offer pickup instead of letting
    the customer reach checkout and fail there.

    Matching is deliberately simple and case-insensitive. Lagos addressing makes
    automated geocoding unreliable, so staff can override the zone on an address
    when the match is wrong.
    """
    haystack = " ".join(part for part in (area, city, street) if part).lower()
    if not haystack.strip():
        return None

    zones = DeliveryZone.objects.filter(branch=branch, is_active=True).order_by(
        "display_order", "name"
    )
    for zone in zones:
        for name in zone.area_names:
            if name and name in haystack:
                return zone
    return None
