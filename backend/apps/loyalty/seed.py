"""Loyalty seed data.

Tiers keep the thresholds and earn multipliers the rewards page advertised,
and nothing else: its "personal concierge", "10% off catering" and "free
birthday dinner for 2" were promises no part of the system keeps, so they are
not seeded as benefits. Birthday points start at 0 until the owner sets them.

Rewards are seeded **inactive** and only where the system can honour them
(money off). "Free drink", "free appetizer" and "VIP experience" named no dish
and are left for staff to create against a real menu item.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.loyalty.models import LoyaltyTier, Reward

TIERS = [
    {"name": "Silver", "min_points": 0, "points_multiplier_bps": 10_000, "colour": "#94a3b8"},
    {"name": "Gold", "min_points": 500, "points_multiplier_bps": 15_000, "colour": "#eab308"},
    {"name": "Platinum", "min_points": 2_000, "points_multiplier_bps": 20_000, "colour": "#9333ea"},
]

REWARDS = [
    {
        "name": "₦500 Off",
        "description": "Your next order",
        "points_cost": 250,
        "value": 50_000,
        "min_order_value": 0,
    },
    {
        "name": "₦1,500 Off",
        "description": "Orders above ₦5,000",
        "points_cost": 750,
        "value": 150_000,
        "min_order_value": 500_000,
    },
    {
        "name": "₦3,000 Off",
        "description": "Orders above ₦10,000",
        "points_cost": 1_500,
        "value": 300_000,
        "min_order_value": 1_000_000,
    },
]


@transaction.atomic
def seed_loyalty(branch: Any, *, stdout: Any = None) -> int:
    created = 0
    for payload in TIERS:
        _, made = LoyaltyTier.objects.get_or_create(name=payload["name"], defaults=payload)
        created += int(made)
    for index, payload in enumerate(REWARDS):
        _, made = Reward.objects.get_or_create(
            branch=branch,
            name=payload["name"],
            defaults={
                **payload,
                "reward_type": "discount",
                "display_order": index,
                "is_active": False,
            },
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} tiers and rewards (rewards inactive until reviewed)")
    return created
