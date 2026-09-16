"""Expiring inactive balances without one query per member.

`expire_inactive` used to ask each account, one at a time, when it was last
active. At 50,000 members that is 50,000 queries inside a task with a
240-second soft limit — so the task was killed partway through, every night,
silently, and the members whose points were actually due to expire were the ones
never reached.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.loyalty import services
from apps.loyalty.models import LedgerEntryType, LoyaltyAccount, PointsLedgerEntry

pytestmark = pytest.mark.django_db


def members(count: int, *, days_ago: int, prefix: str = "m") -> list[LoyaltyAccount]:
    """``count`` members, each with 100 points last touched ``days_ago`` days ago."""
    accounts = []
    for index in range(count):
        user = User.objects.create_user(email=f"{prefix}{index}@example.com", password="x" * 16)
        account = services.get_account(user)
        services.post_entry(
            account=account,
            entry_type=LedgerEntryType.EARN,
            points=100,
            description="An order",
        )
        accounts.append(account)
    PointsLedgerEntry.objects.filter(account__in=accounts).update(
        created_at=timezone.now() - dt.timedelta(days=days_ago)
    )
    for account in accounts:
        account.refresh_from_db()
    return accounts


def scan_cost() -> int:
    with CaptureQueriesContext(connection) as captured:
        services.expire_inactive()
    return len(captured)


# ── The scan ──────────────────────────────────────────────────────────────────


def test_the_scan_does_not_grow_with_the_membership(branch) -> None:  # type: ignore[no-untyped-def]
    """The whole point. Three members and twenty-three cost the same."""
    members(3, days_ago=1, prefix="few")
    few = scan_cost()

    members(20, days_ago=1, prefix="many")
    many = scan_cost()

    assert few == many == 1


def test_an_index_covers_my_points_history(db) -> None:  # type: ignore[no-untyped-def]
    """`(account, -created_at)` — the only way this table is ever read."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, PointsLedgerEntry._meta.db_table
        )
    assert any(
        entry["index"] and entry["columns"] == ["account_id", "created_at"]
        for entry in constraints.values()
    )


# ── The expiry itself ─────────────────────────────────────────────────────────


def test_every_stale_balance_expires(branch) -> None:  # type: ignore[no-untyped-def]
    accounts = members(5, days_ago=400, prefix="old")
    assert services.expire_inactive() == 5
    for account in accounts:
        account.refresh_from_db()
        assert account.points_balance == 0


def test_recently_active_balances_are_left_alone(branch) -> None:  # type: ignore[no-untyped-def]
    accounts = members(4, days_ago=10, prefix="recent")
    assert services.expire_inactive() == 0
    for account in accounts:
        account.refresh_from_db()
        assert account.points_balance == 100


def test_a_second_run_the_same_day_changes_nothing(branch) -> None:  # type: ignore[no-untyped-def]
    members(2, days_ago=400, prefix="twice")
    assert services.expire_inactive() == 2
    assert services.expire_inactive() == 0


def test_an_account_already_expired_today_does_not_spin_forever(branch) -> None:  # type: ignore[no-untyped-def]
    """Why the walk is by primary key rather than by re-running the filter.

    This account still has a balance and is still stale, so it stays in the
    candidate set — and re-reading the first page would hand it back forever.
    """
    account = members(1, days_ago=400, prefix="stuck")[0]
    stamp = timezone.now().date().isoformat()
    PointsLedgerEntry.objects.create(
        account=account,
        entry_type=LedgerEntryType.EXPIRE,
        points=0,
        description="Posted earlier today",
        idempotency_key=f"expire:{account.pk}:{stamp}",
    )

    assert services.expire_inactive() == 0

    account.refresh_from_db()
    assert account.points_balance == 100


def test_a_closed_account_is_not_touched(branch) -> None:  # type: ignore[no-untyped-def]
    account = members(1, days_ago=400, prefix="closed")[0]
    account.is_closed = True
    account.save()
    assert services.expire_inactive() == 0


def test_the_programme_is_cached_and_dropped_when_a_tier_changes(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    from django.urls import reverse

    from apps.loyalty.models import LoyaltyTier

    url = reverse("v1:loyalty:programme")
    silver = LoyaltyTier.objects.create(name="Silver", min_points=0)
    assert [tier["name"] for tier in api_client.get(url).json()["tiers"]] == ["Silver"]

    LoyaltyTier.objects.create(name="Gold", min_points=500)
    assert [tier["name"] for tier in api_client.get(url).json()["tiers"]] == ["Silver", "Gold"]

    silver.delete()
    assert [tier["name"] for tier in api_client.get(url).json()["tiers"]] == ["Gold"]
