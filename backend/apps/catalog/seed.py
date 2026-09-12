"""Catalogue seed data.

Mirrors ``frontend/lib/data/menu.ts`` so the system has the right shape from day
one. **Every price here is a known-wrong placeholder** — the frontend's figures
are dollar amounts wearing a naira sign (₦14.90 for a grill plate). They are
seeded with ``needs_repricing=True``, which hides them from the public API and
fails ``manage.py check --deploy`` until someone sets real prices.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db import transaction

from apps.catalog.models import (
    AvailabilityWindow,
    Category,
    DietaryTag,
    MenuItem,
    Modifier,
    ModifierGroup,
    Variant,
)
from apps.core.models import Branch, Weekday

DIETARY_TAGS: list[dict[str, Any]] = [
    {"name": "Vegetarian", "slug": "vegetarian", "icon": "🥬", "display_order": 1},
    {"name": "Vegan", "slug": "vegan", "icon": "🌱", "display_order": 2},
    {"name": "Gluten free", "slug": "gluten-free", "icon": "🌾", "display_order": 3},
    {"name": "Halal", "slug": "halal", "icon": "☪️", "display_order": 4},
    {"name": "Spicy", "slug": "spicy", "icon": "🌶️", "display_order": 5},
    {"name": "Chef's special", "slug": "chefs-special", "icon": "👨‍🍳", "display_order": 6},
    {
        "name": "Contains nuts",
        "slug": "contains-nuts",
        "icon": "🥜",
        "is_allergen": True,
        "display_order": 7,
    },
    {
        "name": "Contains dairy",
        "slug": "contains-dairy",
        "icon": "🥛",
        "is_allergen": True,
        "display_order": 8,
    },
]

CATEGORIES: list[dict[str, Any]] = [
    {"slug": "whats-hot", "name": "What's Hot", "emoji": "🔥", "display_order": 1},
    {"slug": "burgers", "name": "Burgers", "emoji": "🍔", "display_order": 2},
    {"slug": "chicken-salad", "name": "Chickens and Salads", "emoji": "🍗", "display_order": 3},
    {"slug": "tacos", "name": "Tacos, Fries & Sides", "emoji": "🌮", "display_order": 4},
    {"slug": "breakfast", "name": "Breakfast", "emoji": "🥞", "display_order": 5},
    {"slug": "desserts", "name": "Desserts and Drinks", "emoji": "🍰", "display_order": 6},
]

# (slug, name, description, PLACEHOLDER price in kobo, tags, prep minutes, featured)
MENU_ITEMS: dict[str, list[tuple[str, str, str, int, list[str], int, bool]]] = {
    "whats-hot": [
        (
            "signature-grill-plate",
            "Signature Grill Plate",
            "Slow-cooked beef with roasted garlic & herbs",
            1490,
            ["halal", "chefs-special"],
            30,
            True,
        ),
        (
            "fire-chicken-combo",
            "Fire Chicken Combo",
            "Crispy chicken, spicy sauce, pickles & slaw",
            1250,
            ["halal", "spicy"],
            25,
            True,
        ),
        (
            "chefs-special-pasta",
            "Chef's Special Pasta",
            "House-made fettuccine, truffle cream, parmesan",
            1390,
            ["vegetarian", "contains-dairy", "chefs-special"],
            22,
            True,
        ),
    ],
    "burgers": [
        (
            "classic-smash-burger",
            "Classic Smash Burger",
            "Double smash patty, American cheese, pickles",
            1090,
            ["halal", "contains-dairy"],
            18,
            False,
        ),
        (
            "bbq-bacon-stack",
            "BBQ Bacon Stack",
            "Beef patty, streaky bacon, BBQ sauce, onion rings",
            1350,
            [],
            20,
            False,
        ),
        (
            "spicy-jalapeno-burger",
            "Spicy Jalapeño Burger",
            "Beef patty, jalapeños, pepper jack, chipotle mayo",
            1190,
            ["spicy", "contains-dairy"],
            20,
            False,
        ),
    ],
    "chicken-salad": [
        (
            "grilled-chicken-breast",
            "Grilled Chicken Breast",
            "Herb-marinated chicken, lemon butter, greens",
            1290,
            ["halal", "gluten-free"],
            25,
            False,
        ),
        (
            "caesar-salad",
            "Caesar Salad",
            "Romaine, parmesan, house-made croutons, anchovy dressing",
            990,
            ["contains-dairy"],
            12,
            False,
        ),
        (
            "crispy-chicken-strips",
            "Crispy Chicken Strips",
            "5 pieces, served with honey mustard & fries",
            1150,
            ["halal"],
            18,
            False,
        ),
    ],
    "tacos": [
        (
            "street-tacos",
            "Street Tacos (3 pcs)",
            "Pulled beef, pico de gallo, avocado, lime",
            1090,
            ["halal"],
            15,
            False,
        ),
        (
            "loaded-fries",
            "Loaded Fries",
            "Seasoned fries, cheese sauce, jalapeños, sour cream",
            750,
            ["vegetarian", "contains-dairy"],
            12,
            False,
        ),
        (
            "onion-rings",
            "Onion Rings",
            "Beer-battered, golden crispy, ranch dip",
            690,
            ["vegetarian"],
            10,
            False,
        ),
    ],
    "breakfast": [
        (
            "full-breakfast-plate",
            "Full Breakfast Plate",
            "Eggs, bacon, sausage, toast, baked beans",
            1190,
            [],
            20,
            False,
        ),
        (
            "pancake-stack",
            "Pancake Stack",
            "3 fluffy pancakes, maple syrup, fresh berries",
            950,
            ["vegetarian", "contains-dairy"],
            15,
            False,
        ),
        (
            "avocado-toast",
            "Avocado Toast",
            "Sourdough, smashed avo, poached egg, chilli flakes",
            1090,
            ["vegetarian"],
            12,
            False,
        ),
    ],
    "desserts": [
        (
            "chocolate-lava-cake",
            "Chocolate Lava Cake",
            "Warm dark chocolate cake, vanilla ice cream",
            790,
            ["vegetarian", "contains-dairy"],
            14,
            False,
        ),
        (
            "berry-cheesecake",
            "Berry Cheesecake",
            "New York style, mixed berry compote",
            850,
            ["vegetarian", "contains-dairy"],
            5,
            False,
        ),
        (
            "classic-milkshake",
            "Classic Milkshake",
            "Vanilla, chocolate or strawberry — your choice",
            690,
            ["vegetarian", "contains-dairy"],
            6,
            False,
        ),
    ],
}

# Breakfast is breakfast-only. The frontend has no way to express this, so its
# breakfast items are orderable at 21:00.
BREAKFAST_WINDOW = (dt.time(7, 0), dt.time(11, 30))

# Option prices are plausible naira expressed in KOBO: ₦1,500.00 is 150_000.
# An earlier revision wrote 150 meaning "₦150" and shipped ₦1.50 extra cheese —
# the exact naira/kobo confusion MoneyField.help_text exists to prevent. The
# test `test_seeded_option_prices_are_naira_scale` now guards this.
VARIANTS: dict[str, list[tuple[str, int, bool]]] = {
    "classic-smash-burger": [
        ("Single", -150_000, False),
        ("Double", 0, True),
        ("Triple", 300_000, False),
    ],
    "classic-milkshake": [("Regular", 0, True), ("Large", 100_000, False)],
    "loaded-fries": [("Regular", 0, True), ("Sharing", 150_000, False)],
}

# name, min_select, max_select, [(option, price_delta, is_default)]
MODIFIER_GROUPS: dict[str, list[tuple[str, int, int, list[tuple[str, int, bool]]]]] = {
    "classic-milkshake": [
        # The description says "your choice", so the choice is mandatory.
        (
            "Choose your flavour",
            1,
            1,
            [("Vanilla", 0, True), ("Chocolate", 0, False), ("Strawberry", 0, False)],
        ),
    ],
    "classic-smash-burger": [
        (
            "Add extras",
            0,
            4,
            [
                ("Extra cheese", 30_000, False),
                ("Bacon", 70_000, False),
                ("Fried egg", 50_000, False),
                ("Jalapeños", 20_000, False),
            ],
        ),
        (
            "Remove",
            0,
            3,
            [("No pickles", 0, False), ("No onions", 0, False), ("No sauce", 0, False)],
        ),
    ],
    "signature-grill-plate": [
        (
            "Choose your side",
            1,
            1,
            [
                ("Seasoned fries", 0, True),
                ("Jollof rice", 50_000, False),
                ("Garden salad", 0, False),
                ("Plantain", 40_000, False),
            ],
        ),
    ],
}


@transaction.atomic
def seed_catalogue(branch: Branch, *, stdout: Any = None) -> dict[str, int]:
    """Create the categories, tags and 18 placeholder-priced menu items.

    Idempotent — safe to run on every deploy.
    """
    counts = {"tags": 0, "categories": 0, "items": 0, "variants": 0, "modifiers": 0, "windows": 0}

    tags: dict[str, DietaryTag] = {}
    for payload in DIETARY_TAGS:
        tag, created = DietaryTag.objects.get_or_create(
            slug=payload["slug"], defaults={k: v for k, v in payload.items() if k != "slug"}
        )
        tags[tag.slug] = tag
        counts["tags"] += int(created)

    categories: dict[str, Category] = {}
    for payload in CATEGORIES:
        category, created = Category.objects.get_or_create(
            branch=branch,
            slug=payload["slug"],
            defaults={k: v for k, v in payload.items() if k != "slug"},
        )
        categories[category.slug] = category
        counts["categories"] += int(created)

    for category_slug, rows in MENU_ITEMS.items():
        category = categories[category_slug]
        for order, (slug, name, description, price, tag_slugs, prep, featured) in enumerate(rows):
            item, created = MenuItem.objects.get_or_create(
                branch=branch,
                slug=slug,
                defaults={
                    "category": category,
                    "name": name,
                    "description": description,
                    "base_price": price,
                    # The whole point: these prices are NOT real.
                    "needs_repricing": True,
                    "prep_time_minutes": prep,
                    "is_featured": featured,
                    "display_order": order,
                },
            )
            counts["items"] += int(created)
            if created:
                item.dietary_tags.set([tags[slug_] for slug_ in tag_slugs if slug_ in tags])

            if created and category_slug == "breakfast":
                starts_at, ends_at = BREAKFAST_WINDOW
                for weekday in Weekday.values:
                    AvailabilityWindow.objects.get_or_create(
                        item=item,
                        weekday=weekday,
                        starts_at=starts_at,
                        defaults={"ends_at": ends_at},
                    )
                    counts["windows"] += 1

            if created and slug in VARIANTS:
                for index, (vname, delta, is_default) in enumerate(VARIANTS[slug]):
                    Variant.objects.get_or_create(
                        item=item,
                        name=vname,
                        defaults={
                            "price_delta": delta,
                            "is_default": is_default,
                            "display_order": index,
                        },
                    )
                    counts["variants"] += 1

            if created and slug in MODIFIER_GROUPS:
                for index, (gname, lo, hi, options) in enumerate(MODIFIER_GROUPS[slug]):
                    group, _ = ModifierGroup.objects.get_or_create(
                        item=item,
                        name=gname,
                        defaults={"min_select": lo, "max_select": hi, "display_order": index},
                    )
                    for option_index, (oname, delta, is_default) in enumerate(options):
                        Modifier.objects.get_or_create(
                            group=group,
                            name=oname,
                            defaults={
                                "price_delta": delta,
                                "is_default": is_default,
                                "display_order": option_index,
                            },
                        )
                        counts["modifiers"] += 1

    if stdout is not None:
        for label, value in counts.items():
            stdout.write(f"  + {value} {label}")
    return counts
