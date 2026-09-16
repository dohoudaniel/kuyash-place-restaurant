"""Read queries for core.

Everything here is read-through cached (``apps/core/cache.py``). The branch, its
weekly schedule and its holiday overrides are single-digit row counts that
change a few times a year and are read on every single request — the audit
measured ``/core/branch/`` at roughly twenty queries, most of them these.

**The branch instance is cached; its opening state is not.** ``is_open_now`` is
a property that asks the schedule at the moment it is called, so a cached
``Branch`` reports the truth about right now. The schedule itself is cached
separately and dropped whenever an ``OpeningHours`` or ``HolidayOverride`` row
changes — see ``apps/core/tests/test_caching.py``, which proves an edited window
is reflected immediately.
"""

from __future__ import annotations

import datetime as dt
from typing import NamedTuple

from apps.core.cache import (
    CURRENT_BRANCH_CACHE_KEY,
    HOLIDAYS_KEY,
    OPENING_HOURS_KEY,
    TTL_LONG,
    TTL_MEDIUM,
    cached,
)
from apps.core.models import Branch


class Window(NamedTuple):
    """One opening window, flattened so it can be cached without a model instance."""

    weekday: int
    opens_at: dt.time
    closes_at: dt.time


class Override(NamedTuple):
    """A holiday override for one date."""

    is_closed: bool
    opens_at: dt.time | None
    closes_at: dt.time | None


def get_current_branch() -> Branch:
    """The single active branch.

    Everything funnels through here so that enabling multi-branch later means
    changing one function, not hunting for ``Branch.objects.first()`` calls —
    and so that one cache entry serves all 38 call sites.
    """
    return cached(CURRENT_BRANCH_CACHE_KEY, TTL_MEDIUM, _load_current_branch)


def _load_current_branch() -> Branch:
    branch = Branch.objects.filter(is_active=True).order_by("created_at").first()
    if branch is None:
        # Deliberately raised rather than cached: "there is no branch" is a
        # broken install, not a result worth remembering.
        raise Branch.DoesNotExist(
            "No active Branch exists. Run `python manage.py seed_initial` to create one."
        )
    return branch


# ── Schedule ──────────────────────────────────────────────────────────────────


def opening_windows(branch: Branch, weekday: int | None = None) -> list[Window]:
    """The branch's open windows, optionally for one weekday.

    Windows marked "closed all day" are dropped when the list is built, so a
    caller never has to remember to filter them out.
    """
    windows = cached(
        OPENING_HOURS_KEY.format(branch=branch.pk),
        TTL_LONG,
        lambda: _load_windows(branch),
    )
    if weekday is None:
        return windows
    return [window for window in windows if window.weekday == weekday]


def _load_windows(branch: Branch) -> list[Window]:
    return [
        Window(row.weekday, row.opens_at, row.closes_at)
        for row in branch.opening_hours.filter(is_closed=False).order_by("weekday", "opens_at")
    ]


def holiday_overrides(branch: Branch) -> dict[dt.date, Override]:
    """Every holiday override for the branch, by date.

    All of them, not a window: a restaurant records a handful a year, and
    ``is_open_at`` is asked about arbitrary dates (a booking next Christmas).
    """
    return cached(
        HOLIDAYS_KEY.format(branch=branch.pk),
        TTL_LONG,
        lambda: _load_overrides(branch),
    )


def _load_overrides(branch: Branch) -> dict[dt.date, Override]:
    return {
        row.date: Override(row.is_closed, row.opens_at, row.closes_at)
        for row in branch.holiday_overrides.all()
    }


def holiday_override_on(branch: Branch, day: dt.date) -> Override | None:
    return holiday_overrides(branch).get(day)


def next_opening(branch: Branch, *, within_days: int = 7) -> dt.datetime | None:
    """When the branch next opens, or ``None`` if not within ``within_days``.

    Lets the UI say "opens tomorrow at 11:00" instead of a bare "closed". This
    used to cost two queries per day looked at — up to sixteen on one page load;
    it is now pure arithmetic over the cached schedule.
    """
    now = branch.local_now()
    overrides = holiday_overrides(branch)
    windows = opening_windows(branch)
    for offset in range(within_days + 1):
        day = now + dt.timedelta(days=offset)
        override = overrides.get(day.date())
        if override is not None and override.is_closed:
            continue
        for window in sorted(
            (w for w in windows if w.weekday == day.weekday()), key=lambda w: w.opens_at
        ):
            candidate = dt.datetime.combine(day.date(), window.opens_at, tzinfo=branch.tzinfo())
            if candidate > now:
                return candidate
    return None
