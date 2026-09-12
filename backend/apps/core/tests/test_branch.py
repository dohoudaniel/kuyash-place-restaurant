"""Branch, opening-hours and core API tests."""

from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse

from apps.core.models import Branch, HolidayOverride, OpeningHours, Service, SiteSettings, Weekday
from apps.core.selectors import get_current_branch, next_opening

pytestmark = pytest.mark.django_db


def _restrict_hours(branch: Branch, opens: dt.time, closes: dt.time) -> None:
    """Replace the fixture's all-day schedule with a narrow window.

    The shared fixture is open 00:00–23:59 so that order tests do not pass or
    fail depending on the time of day. Tests about opening hours set their own.
    """
    branch.opening_hours.all().delete()
    for weekday in Weekday.values:
        OpeningHours.objects.create(
            branch=branch,
            weekday=weekday,
            service=Service.ALL_DAY,
            opens_at=opens,
            closes_at=closes,
        )


def test_branch_is_open_within_published_hours(branch: Branch) -> None:
    _restrict_hours(branch, dt.time(11, 0), dt.time(22, 0))
    monday_lunch = dt.datetime(2026, 9, 14, 13, 0, tzinfo=branch.tzinfo())  # a Monday
    assert branch.is_open_at(monday_lunch) is True


def test_branch_is_closed_outside_published_hours(branch: Branch) -> None:
    _restrict_hours(branch, dt.time(11, 0), dt.time(22, 0))
    monday_dawn = dt.datetime(2026, 9, 14, 3, 0, tzinfo=branch.tzinfo())
    assert branch.is_open_at(monday_dawn) is False


def test_holiday_override_closes_the_branch(branch: Branch) -> None:
    """An override wins over the weekly schedule."""
    _restrict_hours(branch, dt.time(11, 0), dt.time(22, 0))
    christmas = dt.date(2026, 12, 25)
    HolidayOverride.objects.create(branch=branch, date=christmas, is_closed=True, note="Christmas")
    midday = dt.datetime(2026, 12, 25, 13, 0, tzinfo=branch.tzinfo())
    assert branch.is_open_at(midday) is False


def test_holiday_override_can_set_special_hours(branch: Branch) -> None:
    _restrict_hours(branch, dt.time(11, 0), dt.time(22, 0))
    day = dt.date(2026, 12, 26)
    HolidayOverride.objects.create(
        branch=branch,
        date=day,
        is_closed=False,
        opens_at=dt.time(16, 0),
        closes_at=dt.time(20, 0),
    )
    assert branch.is_open_at(dt.datetime(2026, 12, 26, 14, 0, tzinfo=branch.tzinfo())) is False
    assert branch.is_open_at(dt.datetime(2026, 12, 26, 17, 0, tzinfo=branch.tzinfo())) is True


def test_can_accept_orders_requires_both_switches(branch: Branch) -> None:
    """Closing the kitchen manually must stop orders even during opening hours."""
    branch.is_accepting_orders = False
    branch.save()
    assert branch.is_accepting_orders is False
    assert branch.can_accept_orders is False


def test_next_opening_finds_a_future_window(branch: Branch) -> None:
    moment = next_opening(branch)
    assert moment is None or moment > branch.local_now()


def test_invalid_timezone_falls_back_to_utc(branch: Branch) -> None:
    """A bad timezone string must not take the whole site down."""
    branch.timezone = "Not/AZone"
    branch.save()
    assert branch.tzinfo() is dt.UTC


def test_get_current_branch_raises_when_none_exists(db) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(Branch.DoesNotExist, match="seed_initial"):
        get_current_branch()


def test_opening_hours_reject_reversed_window(branch: Branch) -> None:
    """A window that closes before it opens is rejected by the database itself."""
    from django.db import transaction
    from django.db.utils import IntegrityError

    with pytest.raises(IntegrityError), transaction.atomic():
        OpeningHours.objects.create(
            branch=branch,
            weekday=Weekday.MONDAY,
            service=Service.BREAKFAST,
            opens_at=dt.time(22, 0),
            closes_at=dt.time(11, 0),
        )


def test_site_settings_is_a_singleton(db) -> None:  # type: ignore[no-untyped-def]
    first = SiteSettings.load()
    first.tagline = "Tastefully Classy"
    first.save()
    second = SiteSettings.load()
    assert SiteSettings.objects.count() == 1
    assert second.tagline == "Tastefully Classy"


# ── API ───────────────────────────────────────────────────────────────────────


def test_branch_endpoint_exposes_vat_policy(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:core:branch"))
    assert response.status_code == 200
    body = response.json()
    assert body["prices_include_vat"] is True
    assert body["vat_rate_bps"] == 750
    assert body["currency"] == "NGN"


def test_branch_endpoint_returns_money_as_wire_objects(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    """Money is never a bare number: clients render `display` and never format."""
    body = api_client.get(reverse("v1:core:branch")).json()
    assert body["min_order_value"] == {
        "amount": 200_000,
        "currency": "NGN",
        "display": "₦2,000.00",
    }


def test_opening_hours_endpoint(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(reverse("v1:core:opening-hours")).json()
    assert len(body["hours"]) == 7
    assert body["timezone"] == "Africa/Lagos"
    assert "is_open_now" in body


def test_settings_endpoint(api_client, db) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:core:settings")).status_code == 200


def test_absent_free_delivery_threshold_serialises_as_null(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    """NULL and ₦0.00 mean opposite things and must not be conflated.

    A null threshold means "delivery is never free". Zero would mean "delivery is
    always free" — the same field, the opposite policy, and a direct revenue leak.
    """
    branch.free_delivery_threshold = None
    branch.save(update_fields=["free_delivery_threshold"])

    body = api_client.get(reverse("v1:core:branch")).json()
    assert body["free_delivery_threshold"] is None


def test_nullable_money_field_has_no_zero_default(branch: Branch) -> None:
    """The model default must be NULL, not 0, for a nullable money column."""
    fresh = Branch.objects.create(name="No Threshold", slug="no-threshold")
    assert fresh.free_delivery_threshold is None
    assert fresh.min_order_value == 0  # non-nullable money still defaults to zero


# ──────────────────────────────────────────────────────────────────────────────
# Admin display columns
# ──────────────────────────────────────────────────────────────────────────────


def test_admin_states_the_vat_direction_in_the_list(branch: Branch) -> None:
    """Whether VAT is inclusive is the one setting staff must not misread."""
    from django.contrib.admin.sites import AdminSite

    from apps.core.admin import BranchAdmin

    admin_instance = BranchAdmin(Branch, AdminSite())
    assert admin_instance.vat_display(branch) == "7.5% (inclusive)"
    assert admin_instance.is_open_now(branch) is True

    branch.prices_include_vat = False
    assert admin_instance.vat_display(branch) == "7.5% (added at checkout)"


def test_site_settings_admin_keeps_the_singleton_single(db) -> None:  # type: ignore[no-untyped-def]
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.core.admin import SiteSettingsAdmin

    admin_instance = SiteSettingsAdmin(SiteSettings, AdminSite())
    request = RequestFactory().get("/admin/core/sitesettings/")

    assert admin_instance.has_add_permission(request) is True
    SiteSettings.load()
    assert admin_instance.has_add_permission(request) is False
    assert admin_instance.has_delete_permission(request) is False
