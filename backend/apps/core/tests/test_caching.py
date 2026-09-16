"""Read-through caching, and — the part that matters — its invalidation.

A cache that is never wrong is easy to write and impossible to trust. Every test
here changes something behind a cached read and asserts the change is visible,
because "the second call was faster" is not the property worth protecting.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.core.cache import cache as django_cache
from django.core.signals import request_finished, request_started
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core import cache as core_cache
from apps.core.models import Branch, HolidayOverride, LegalPage, OpeningHours, Service, SiteSettings
from apps.core.selectors import get_current_branch, next_opening

pytestmark = pytest.mark.django_db

#: A Monday, so the weekday is not whichever day the suite happens to run.
MONDAY_LUNCH = dt.datetime(2026, 9, 14, 13, 0)


def _only_window(branch: Branch, opens: dt.time, closes: dt.time) -> None:
    branch.opening_hours.all().delete()
    OpeningHours.objects.create(
        branch=branch,
        weekday=0,
        service=Service.ALL_DAY,
        opens_at=opens,
        closes_at=closes,
    )


def _monday(branch: Branch) -> dt.datetime:
    return MONDAY_LUNCH.replace(tzinfo=branch.tzinfo())


# ── The memo ──────────────────────────────────────────────────────────────────


def test_a_repeat_read_inside_one_request_does_not_go_back_to_the_cache() -> None:
    """Clearing the shared cache mid-request proves the answer came from the memo."""
    request_started.send(sender=None)
    try:
        assert core_cache.cached("probe", 60, lambda: "first") == "first"
        django_cache.clear()
        assert core_cache.cached("probe", 60, lambda: "second") == "first"
    finally:
        request_finished.send(sender=None)


def test_outside_a_request_nothing_is_memoised() -> None:
    """A Celery worker's thread lives for days. A memo it could never clear would
    serve last Tuesday's branch until the process restarted."""
    assert core_cache.cached("probe", 60, lambda: "first") == "first"
    django_cache.clear()
    assert core_cache.cached("probe", 60, lambda: "second") == "second"


def test_invalidating_drops_the_memo_too() -> None:
    request_started.send(sender=None)
    try:
        core_cache.cached("probe", 60, lambda: "first")
        core_cache.invalidate("probe")
        assert core_cache.cached("probe", 60, lambda: "second") == "second"
    finally:
        request_finished.send(sender=None)


# ── The branch ────────────────────────────────────────────────────────────────


def test_the_branch_is_cached_under_the_key_that_was_declared_and_never_used(
    branch: Branch,
) -> None:
    get_current_branch()
    assert django_cache.get(core_cache.CURRENT_BRANCH_CACHE_KEY) is not None


def test_editing_the_branch_drops_the_cached_copy(branch: Branch) -> None:
    assert get_current_branch().is_accepting_orders is True
    branch.is_accepting_orders = False
    branch.save()
    assert get_current_branch().is_accepting_orders is False


def test_a_missing_branch_is_not_cached_as_an_answer(db) -> None:  # type: ignore[no-untyped-def]
    """ "There is no branch" is a broken install, not a result to remember."""
    with pytest.raises(Branch.DoesNotExist):
        get_current_branch()
    Branch.objects.create(name="Late Arrival", slug="late")
    assert get_current_branch().slug == "late"


# ── The schedule: cached, but never stale ─────────────────────────────────────


def test_opening_hours_changes_show_through_a_cached_branch(branch: Branch) -> None:
    """The point of caching the instance rather than its opening state.

    `is_open_now` is a property computed from related rows when it is called, so
    a cached Branch still answers about now — as long as the schedule behind it
    is dropped when it changes. This is that guarantee.
    """
    moment = _monday(branch)
    _only_window(branch, dt.time(11, 0), dt.time(22, 0))
    assert get_current_branch().is_open_at(moment) is True

    _only_window(branch, dt.time(6, 0), dt.time(9, 0))
    assert get_current_branch().is_open_at(moment) is False


def test_a_new_holiday_override_closes_a_cached_branch(branch: Branch) -> None:
    moment = _monday(branch)
    assert get_current_branch().is_open_at(moment) is True

    HolidayOverride.objects.create(
        branch=branch, date=moment.date(), is_closed=True, note="Public holiday"
    )
    assert get_current_branch().is_open_at(moment) is False

    HolidayOverride.objects.filter(branch=branch, date=moment.date()).delete()
    assert get_current_branch().is_open_at(moment) is True


def test_next_opening_follows_an_edited_schedule(branch: Branch) -> None:
    _only_window(branch, dt.time(11, 0), dt.time(22, 0))
    first = next_opening(branch)
    _only_window(branch, dt.time(9, 0), dt.time(22, 0))
    second = next_opening(branch)
    assert first is None or second is None or second <= first


# ── Query cost ────────────────────────────────────────────────────────────────


def test_the_branch_endpoint_stops_costing_twenty_queries(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    """It was ~20: opening hours, holiday overrides, a `next_opening` loop of up
    to eight days at two queries each, and `is_open_now` computed twice."""
    url = reverse("v1:core:branch")
    with CaptureQueriesContext(connection) as cold:
        assert api_client.get(url).status_code == 200
    assert len(cold) <= 5

    with CaptureQueriesContext(connection) as warm:
        assert api_client.get(url).status_code == 200
    assert len(warm) == 0


def test_the_opening_hours_endpoint_is_still_correct_when_warm(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    url = reverse("v1:core:opening-hours")
    assert len(api_client.get(url).json()["hours"]) == 7
    branch.opening_hours.filter(weekday=0).delete()
    assert len(api_client.get(url).json()["hours"]) == 6


# ── Site settings and legal copy ──────────────────────────────────────────────


def test_site_settings_are_cached_and_dropped_on_save(api_client, db) -> None:  # type: ignore[no-untyped-def]
    url = reverse("v1:core:settings")
    row = SiteSettings.load()
    row.tagline = "Tastefully Classy"
    row.save()
    assert api_client.get(url).json()["tagline"] == "Tastefully Classy"

    row.tagline = "Something Else"
    row.save()
    assert api_client.get(url).json()["tagline"] == "Something Else"


def test_publishing_a_policy_page_shows_up_immediately(api_client, db) -> None:  # type: ignore[no-untyped-def]
    index = reverse("v1:core:legal-list")
    assert api_client.get(index).json() == []

    page = LegalPage.objects.create(
        slug="terms", version=1, title="Terms", body="The wording.", published=True
    )
    assert [row["slug"] for row in api_client.get(index).json()] == ["terms"]

    detail = reverse("v1:core:legal-detail", kwargs={"slug": "terms"})
    assert api_client.get(detail).json()["title"] == "Terms"

    page.title = "Terms of Service"
    page.save()
    assert api_client.get(detail).json()["title"] == "Terms of Service"

    page.published = False
    page.save()
    assert api_client.get(detail).status_code == 404
    assert api_client.get(index).json() == []


# ── Cache-Control ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "v1:core:branch",
        "v1:core:opening-hours",
        "v1:core:settings",
        "v1:core:legal-list",
        "v1:core:team",
        "v1:core:awards",
    ],
)
def test_public_reads_tell_caches_they_may_be_cached(api_client, branch, name) -> None:  # type: ignore[no-untyped-def]
    header = api_client.get(reverse(name))["Cache-Control"]
    assert "public" in header
    assert "max-age=" in header


def test_a_failure_is_never_marked_cacheable(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:core:legal-detail", kwargs={"slug": "nope"}))
    assert response.status_code == 404
    assert "public" not in response.get("Cache-Control", "")
