"""Deployment checks for the catalogue."""

from __future__ import annotations

from typing import Any

from django.core.checks import Error, register


@register("kuyash", deploy=True)
def check_no_unpriced_items(app_configs: Any, **kwargs: Any) -> list[Error]:
    """Refuse to deploy while any live item still carries a placeholder price.

    The seeded prices are the frontend's figures — ₦14.90 for a grill plate,
    ₦10.90 for a burger — which are dollar amounts wearing a naira sign. This
    check is what turns "remember to reprice before launch" into something the
    build enforces.

    Runs only under ``manage.py check --deploy``.
    """
    from django.db import OperationalError, ProgrammingError

    from apps.catalog.models import MenuItem

    try:
        unpriced = list(
            MenuItem.objects.filter(is_active=True, needs_repricing=True).values_list(
                "slug", flat=True
            )[:20]
        )
        total = MenuItem.objects.filter(is_active=True, needs_repricing=True).count()
    except (OperationalError, ProgrammingError):
        # Database not migrated yet (fresh CI checkout) — nothing to assert.
        return []

    if not unpriced:
        return []

    listed = ", ".join(unpriced)
    if total > len(unpriced):
        listed += f", … ({total} total)"

    return [
        Error(
            f"{total} active menu item(s) still have placeholder prices.",
            hint=(
                "Set real naira prices in the admin and clear 'needs repricing'. "
                f"Affected: {listed}. These items are hidden from the public API "
                "until the flag is cleared. See docs/ROADMAP.md Gate 1."
            ),
            id="kuyash.E001",
        )
    ]
