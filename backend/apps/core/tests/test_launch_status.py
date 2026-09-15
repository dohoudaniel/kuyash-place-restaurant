"""``manage.py launch_status`` — one report of what stands between us and launch."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.management.commands import launch_status

pytestmark = pytest.mark.django_db


def report(*, raises: bool = False) -> dict[str, Any]:
    out = io.StringIO()
    if raises:
        with pytest.raises(CommandError):
            call_command("launch_status", "--json", stdout=out)
    else:
        call_command("launch_status", "--json", stdout=out)
    return dict(json.loads(out.getvalue()))


def item(data: dict[str, Any], name: str) -> dict[str, Any]:
    return next(entry for entry in data["items"] if entry["name"] == name)


@pytest.fixture
def clean_checks(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(launch_status, "run_checks", lambda **kwargs: [])


@pytest.fixture
def ready_environment(settings, clean_checks, kitchen_user, manager_user):  # type: ignore[no-untyped-def]
    from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

    from apps.accounts.models import User
    from apps.common.tasks import heartbeat

    settings.SENTRY_DSN = "https://public@example.invalid/1"
    settings.ADMIN_ALLOWED_IPS = ["198.51.100.0/24"]
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.STAFF_MFA_REQUIRED = True
    heartbeat()
    staff = User.objects.create_user(email="owner@example.com", password="x" * 16, is_staff=True)
    TOTP.activate(staff, generate_totp_secret())


def test_a_ready_environment_reports_ready(ready_environment) -> None:  # type: ignore[no-untyped-def]
    data = report()
    assert data["ready"] is True
    states = {entry["state"] for entry in data["items"]}
    assert states == {"done", "manual"}


def test_error_level_checks_block_and_fail_the_command(ready_environment, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        launch_status,
        "run_checks",
        lambda **kwargs: [
            Error("3 dishes need prices", hint="Set them in admin", id="kuyash.E001")
        ],
    )
    data = report(raises=True)
    entry = item(data, "kuyash.E001")
    assert entry["state"] == "blocking"
    assert "Set them in admin" in entry["detail"]
    assert data["ready"] is False


def test_warnings_are_to_do_not_blocking(ready_environment, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        launch_status,
        "run_checks",
        lambda **kwargs: [CheckWarning("Terms unpublished", id="kuyash.W003")],
    )
    data = report()
    assert item(data, "kuyash.W003")["state"] == "todo"
    assert data["ready"] is False


def test_the_real_project_checks_are_what_it_runs(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    seen: dict[str, Any] = {}

    def spy(**kwargs: Any) -> list[Any]:
        seen.update(kwargs)
        return []

    monkeypatch.setattr(launch_status, "run_checks", spy)
    report()
    assert seen == {"tags": ["kuyash"], "include_deployment_checks": True}


def test_an_unconfigured_environment_lists_what_to_do(clean_checks, settings) -> None:  # type: ignore[no-untyped-def]
    settings.ADMIN_ALLOWED_IPS = []
    data = report()
    for name in (
        "Error reporting",
        "Admin allowlist",
        "Scheduled work",
        "Staff two-factor",
        "Kitchen team",
        "Managers",
    ):
        assert item(data, name)["state"] == "todo", name
    assert "nobody can use the kitchen display" in item(data, "Kitchen team")["detail"]


def test_staff_missing_two_factor_are_named(ready_environment) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    User.objects.create_user(email="new-staff@example.com", password="x" * 16, is_staff=True)
    entry = item(report(), "Staff two-factor")
    assert entry["state"] == "todo"
    assert "new-staff@example.com" in entry["detail"]


def test_a_stopped_scheduler_is_reported(ready_environment) -> None:  # type: ignore[no-untyped-def]
    from django.core.cache import cache

    from apps.common.tasks import HEARTBEAT_KEY

    cache.delete(HEARTBEAT_KEY)
    entry = item(report(), "Scheduled work")
    assert entry["state"] == "todo" and "not seen" in entry["detail"]


def test_riders_matter_only_once_delivery_is_open(ready_environment, zone) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User
    from apps.delivery.models import RiderProfile, VehicleType

    assert item(report(), "Riders")["state"] == "todo"
    user = User.objects.create_user(email="rider@example.com", password="x" * 16)
    RiderProfile.objects.create(user=user, vehicle_type=VehicleType.values[0])
    assert item(report(), "Riders")["state"] == "done"


def test_without_delivery_zones_riders_are_not_listed(ready_environment) -> None:  # type: ignore[no-untyped-def]
    assert not [entry for entry in report()["items"] if entry["name"] == "Riders"]


def test_the_human_report_groups_and_marks_items(ready_environment, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = io.StringIO()
    call_command("launch_status", stdout=out)
    text = out.getvalue()
    assert "System checks" in text and "By hand" in text
    assert "✓ Kitchen team" in text and "☐ Backups" in text
    assert "Everything checkable is ready." in text


def test_pending_migrations_block_and_skip_staffing(ready_environment, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """An unmigrated database is reported, not a crash on a missing table."""
    from django.db.migrations.executor import MigrationExecutor

    class Pending:
        app_label = "mfa"
        name = "0001_initial"

    monkeypatch.setattr(
        MigrationExecutor, "migration_plan", lambda self, targets: [(Pending(), False)]
    )
    data = report(raises=True)
    entry = item(data, "Migrations")
    assert entry["state"] == "blocking" and "mfa.0001_initial" in entry["detail"]
    assert not [e for e in data["items"] if e["area"] == "People"]
