"""Pytest configuration shared by every test module."""

from __future__ import annotations

import pytest


@pytest.fixture
def branch(db):  # type: ignore[no-untyped-def]
    """A seeded branch open 11:00–22:00 every day, VAT-inclusive at 7.5%."""
    import datetime as dt

    from apps.core.models import Branch, OpeningHours, Service, Weekday

    obj = Branch.objects.create(
        name="Kuyash Place — Test",
        slug="test-branch",
        city="Lagos",
        state="Lagos",
        prices_include_vat=True,
        vat_rate_bps=750,
        min_order_value=200_000,
        free_delivery_threshold=1_500_000,
    )
    for weekday in Weekday.values:
        OpeningHours.objects.create(
            branch=obj,
            weekday=weekday,
            service=Service.ALL_DAY,
            opens_at=dt.time(11, 0),
            closes_at=dt.time(22, 0),
        )
    return obj


@pytest.fixture
def user(db):  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    return User.objects.create_user(
        email="ada@example.com",
        password="correct-horse-battery-staple",
        full_name="Ada Obi",
        phone="+2348012345678",
    )


@pytest.fixture
def api_client():  # type: ignore[no-untyped-def]
    from rest_framework.test import APIClient

    return APIClient()
