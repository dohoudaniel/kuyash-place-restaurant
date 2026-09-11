"""The seed command must be idempotent — it is run on every deploy."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.core.models import Branch, OpeningHours, SiteSettings

pytestmark = pytest.mark.django_db


def test_seed_creates_baseline(capsys) -> None:  # type: ignore[no-untyped-def]
    call_command("seed_initial")
    assert Branch.objects.count() == 1
    assert OpeningHours.objects.count() == 7
    assert SiteSettings.objects.count() == 1
    assert (
        Group.objects.filter(name__in=["customers", "kitchen", "riders", "managers"]).count() == 4
    )


def test_seed_is_idempotent() -> None:
    call_command("seed_initial")
    call_command("seed_initial")
    assert Branch.objects.count() == 1
    assert OpeningHours.objects.count() == 7
    assert SiteSettings.objects.count() == 1


def test_seed_warns_that_prices_are_placeholders(capsys) -> None:  # type: ignore[no-untyped-def]
    """Gate 1 depends on someone actually noticing this."""
    call_command("seed_initial")
    assert "PLACEHOLDER" in capsys.readouterr().out
