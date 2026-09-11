"""Read queries for core."""

from __future__ import annotations

import datetime as dt

from apps.core.models import Branch

CURRENT_BRANCH_CACHE_KEY = "core:current_branch_id"


def get_current_branch() -> Branch:
    """The single active branch.

    Everything funnels through here so that enabling multi-branch later means
    changing one function, not hunting for ``Branch.objects.first()`` calls.
    """
    branch = Branch.objects.filter(is_active=True).order_by("created_at").first()
    if branch is None:
        raise Branch.DoesNotExist(
            "No active Branch exists. Run `python manage.py seed_initial` to create one."
        )
    return branch


def next_opening(branch: Branch, *, within_days: int = 7) -> dt.datetime | None:
    """When the branch next opens, or ``None`` if not within ``within_days``.

    Lets the UI say "opens tomorrow at 11:00" instead of a bare "closed".
    """
    now = branch.local_now()
    for offset in range(within_days + 1):
        day = now + dt.timedelta(days=offset)
        override = branch.holiday_overrides.filter(date=day.date()).first()
        if override is not None and override.is_closed:
            continue
        windows = branch.opening_hours.filter(weekday=day.weekday(), is_closed=False)
        for window in windows.order_by("opens_at"):
            candidate = dt.datetime.combine(day.date(), window.opens_at, tzinfo=branch.tzinfo())
            if candidate > now:
                return candidate
    return None
