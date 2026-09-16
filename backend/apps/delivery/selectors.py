"""Zone resolution."""

from __future__ import annotations

from apps.core.models import Branch
from apps.delivery.models import DeliveryArea, DeliveryZone, normalise_area

#: The longest area name worth looking for, in words. "Lekki Phase 1" is three;
#: six leaves room without turning a long address into hundreds of candidates.
MAX_AREA_WORDS = 6


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

    **How it works.** The address is folded to words, every run of up to
    ``MAX_AREA_WORDS`` consecutive words becomes a candidate, and one indexed
    ``IN`` lookup finds the zones whose area names are among them. This replaced
    loading every active zone and running Python substring matching over every
    one of its names, on every address save and every checkout price.

    One behavioural difference, and it is an improvement: candidates are whole
    words, so "VI" no longer matches inside "Victoria Island" — an area named
    "VI" still matches an address that says VI.
    """
    haystack = normalise_area(" ".join(part for part in (area, city, street) if part))
    if not haystack:
        return None

    words = haystack.split()
    candidates = {
        " ".join(words[start : start + length])
        for length in range(1, MAX_AREA_WORDS + 1)
        for start in range(len(words) - length + 1)
    }
    if not candidates:
        return None

    match = (
        DeliveryArea.objects.filter(
            normalised__in=candidates, zone__branch=branch, zone__is_active=True
        )
        .select_related("zone")
        .order_by("zone__display_order", "zone__name")
        .first()
    )
    return match.zone if match else None
