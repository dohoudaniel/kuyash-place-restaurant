"""Reservation seed data.

Areas mirror ``TableSelection.tsx``; the tables and service periods are the
part the frontend has no concept of at all.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db import transaction

from apps.core.models import Branch, Weekday
from apps.reservations.models import RestaurantTable, ServicePeriod, TableArea

AREAS: list[dict[str, Any]] = [
    {
        "slug": "indoor",
        "name": "Indoor Seating",
        "display_order": 1,
        "description": "Climate-controlled comfort with ambient lighting.",
        "features": ["Air conditioned", "Ambient music", "Cosy atmosphere"],
    },
    {
        "slug": "outdoor",
        "name": "Outdoor Patio",
        "display_order": 2,
        "description": "Fresh air and garden views.",
        "features": ["Garden views", "Natural light", "Al fresco dining"],
    },
    {
        "slug": "private",
        "name": "Private Room",
        "display_order": 3,
        "description": "Exclusive space for special occasions.",
        "features": ["Private space", "Dedicated service", "Custom menu"],
        "is_premium": True,
        # PLACEHOLDER, like every other seeded price. ₦25,000.00 in kobo.
        "surcharge": 2_500_000,
    },
]

# (area slug, table number, seats_min, seats_max)
TABLES: list[tuple[str, str, int, int]] = [
    ("indoor", "1", 1, 2),
    ("indoor", "2", 1, 2),
    ("indoor", "3", 2, 4),
    ("indoor", "4", 2, 4),
    ("indoor", "5", 2, 4),
    ("indoor", "6", 4, 6),
    ("indoor", "7", 4, 6),
    ("indoor", "8", 6, 8),
    ("outdoor", "P1", 2, 4),
    ("outdoor", "P2", 2, 4),
    ("outdoor", "P3", 4, 6),
    ("outdoor", "P4", 4, 8),
    ("private", "R1", 8, 16),
    ("private", "R2", 10, 20),
]

# (name, weekday range, opens, last seating, slot minutes, turn minutes)
PERIODS: list[tuple[str, dt.time, dt.time, int, int]] = [
    ("Lunch", dt.time(12, 0), dt.time(15, 0), 30, 90),
    ("Dinner", dt.time(18, 0), dt.time(21, 30), 30, 120),
]


@transaction.atomic
def seed_reservations(branch: Branch, *, stdout: Any = None) -> dict[str, int]:
    """Create areas, tables and service periods. Idempotent."""
    counts = {"areas": 0, "tables": 0, "periods": 0}

    areas: dict[str, TableArea] = {}
    for payload in AREAS:
        area, created = TableArea.objects.get_or_create(
            branch=branch,
            slug=payload["slug"],
            defaults={k: v for k, v in payload.items() if k != "slug"},
        )
        areas[area.slug] = area
        counts["areas"] += int(created)

    for area_slug, number, seats_min, seats_max in TABLES:
        _, created = RestaurantTable.objects.get_or_create(
            branch=branch,
            number=number,
            defaults={
                "area": areas[area_slug],
                "seats_min": seats_min,
                "seats_max": seats_max,
            },
        )
        counts["tables"] += int(created)

    for name, starts, ends, slot, turn in PERIODS:
        for weekday in Weekday.values:
            _, created = ServicePeriod.objects.get_or_create(
                branch=branch,
                weekday=weekday,
                name=name,
                defaults={
                    "starts_at": starts,
                    "ends_at": ends,
                    "slot_interval_minutes": slot,
                    "turn_time_minutes": turn,
                },
            )
            counts["periods"] += int(created)

    if stdout is not None:
        for label, value in counts.items():
            stdout.write(f"  + {value} {label}")
    return counts
