"""Catering seed data.

The three packages from ``app/catering/page.tsx``. Unlike the menu, these
figures were already priced natively in naira (₦3,500–₦12,000 per head), so
they convert directly rather than needing the repricing gate.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.catering.models import CateringPackage
from apps.core.models import Branch

PACKAGES: list[dict[str, Any]] = [
    {
        "slug": "essential",
        "name": "Essential",
        "display_order": 1,
        "description": "Perfect for small gatherings and casual events.",
        "min_guests": 10,
        "max_guests": 30,
        "price_per_person": 350_000,  # ₦3,500.00
        "features": [
            "2 Main Dishes (choice of Nigerian classics)",
            "1 Side Dish",
            "Soft Drinks & Water",
            "Basic Setup & Cleanup",
            "Disposable Plates & Cutlery",
        ],
    },
    {
        "slug": "premium",
        "name": "Premium",
        "display_order": 2,
        "is_popular": True,
        "description": "Ideal for corporate events and special occasions.",
        "min_guests": 30,
        "max_guests": 100,
        "price_per_person": 650_000,  # ₦6,500.00
        "features": [
            "4 Main Dishes (premium selection)",
            "3 Side Dishes",
            "Appetizers & Small Chops",
            "Soft Drinks, Juice & Water",
            "Professional Serving Staff",
            "China Plates & Silverware",
            "Elegant Table Setup",
            "Full Cleanup Service",
        ],
    },
    {
        "slug": "luxury",
        "name": "Luxury",
        "display_order": 3,
        "description": "Ultimate experience for weddings and galas.",
        "min_guests": 100,
        "max_guests": 500,
        "price_per_person": 1_200_000,  # ₦12,000.00
        "features": [
            "6+ Main Dishes (gourmet selection)",
            "5 Side Dishes",
            "Premium Appetizers & Canapés",
            "Full Beverage Service (non-alcoholic)",
            "Live Cooking Stations",
            "Professional Chefs & Waitstaff",
            "Premium Tableware & Linens",
            "Event Coordination",
            "Custom Menu Design",
            "Decorative Food Presentation",
        ],
    },
]


@transaction.atomic
def seed_catering(branch: Branch, *, stdout: Any = None) -> int:
    """Create the catering packages. Idempotent."""
    created = 0
    for payload in PACKAGES:
        _, made = CateringPackage.objects.get_or_create(
            branch=branch,
            slug=payload["slug"],
            defaults={k: v for k, v in payload.items() if k != "slug"},
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} catering packages")
    return created
