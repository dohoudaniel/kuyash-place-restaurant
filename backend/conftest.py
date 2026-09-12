"""Pytest configuration shared by every test module."""

from __future__ import annotations

import pytest
from django.conf import settings

#: Skip marker for tests that need real row locking. SQLite serialises
#: writers with a table lock, so a threaded write test measures SQLite, not
#: the application (ADR-015). CI runs these against Postgres.
requires_postgres = pytest.mark.skipif(
    not settings.USING_POSTGRES,
    reason="needs row-level locking; SQLite locks the whole table (ADR-015)",
)


@pytest.fixture
def branch(db):  # type: ignore[no-untyped-def]
    """A branch open around the clock, VAT-inclusive at 7.5%.

    Deliberately open 00:00–23:59: a narrower window would make every test that
    places an order pass or fail depending on the time of day it was run. Tests
    that exercise opening-hours logic build their own windows and moments
    explicitly (see apps/core/tests/test_branch.py).
    """
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
            opens_at=dt.time(0, 0),
            closes_at=dt.time(23, 59),
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


@pytest.fixture
def category(db, branch):  # type: ignore[no-untyped-def]
    from apps.catalog.models import Category

    return Category.objects.create(
        branch=branch, name="Burgers", slug="burgers", emoji="🍔", display_order=1
    )


@pytest.fixture
def menu_item(db, branch, category):  # type: ignore[no-untyped-def]
    """A fully priced, orderable item. Prices are explicit kobo, never Decimal."""
    from apps.catalog.models import MenuItem

    return MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Classic Smash Burger",
        slug="classic-smash-burger",
        description="Double smash patty, American cheese, pickles",
        base_price=1_090_000,  # ₦10,900.00 — a plausible naira price
        needs_repricing=False,
        prep_time_minutes=18,
    )


@pytest.fixture
def unpriced_item(db, branch, category):  # type: ignore[no-untyped-def]
    """An item still carrying a placeholder price."""
    from apps.catalog.models import MenuItem

    return MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Placeholder Burger",
        slug="placeholder-burger",
        base_price=1090,  # the frontend's ₦10.90 — a dollar figure
        needs_repricing=True,
    )


@pytest.fixture
def zone(db, branch):  # type: ignore[no-untyped-def]
    from apps.delivery.models import DeliveryZone

    return DeliveryZone.objects.create(
        branch=branch,
        name="Victoria Island",
        slug="victoria-island",
        fee=150_000,
        min_order_value=200_000,
        estimated_minutes=35,
        areas=["Victoria Island", "VI", "Eko Atlantic"],
    )


@pytest.fixture
def verified_user(db):  # type: ignore[no-untyped-def]
    """A user who has confirmed their email and can therefore sign in."""
    from allauth.account.models import EmailAddress

    from apps.accounts.models import User

    user = User.objects.create_user(
        email="ada@example.com",
        password="correct-horse-battery-staple",
        full_name="Ada Obi",
        phone="+2348012345678",
    )
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    return user


@pytest.fixture(autouse=True)
def _clear_cache():  # type: ignore[no-untyped-def]
    """Reset the cache between tests.

    Throttle counters live in the cache, and LocMemCache is process-wide: without
    this, one test's requests count against the next test's rate limit.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def throttle_rates():  # type: ignore[no-untyped-def]
    """Temporarily enable specific throttle scopes.

    ``override_settings(REST_FRAMEWORK=...)`` does not work here: DRF binds
    ``SimpleRateThrottle.THROTTLE_RATES`` to a dict object at class-definition
    time, so replacing the settings dict leaves the class attribute pointing at
    the original. The class attribute has to be patched directly.
    """
    import contextlib

    from rest_framework.throttling import SimpleRateThrottle

    @contextlib.contextmanager
    def _apply(**scopes: str | None):  # type: ignore[no-untyped-def]
        original = SimpleRateThrottle.THROTTLE_RATES
        SimpleRateThrottle.THROTTLE_RATES = {**original, **scopes}
        try:
            yield
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original

    return _apply


@pytest.fixture
def cart(db, branch):  # type: ignore[no-untyped-def]
    from apps.carts.models import Cart

    return Cart.objects.create(branch=branch)


@pytest.fixture
def user_cart(db, branch, verified_user):  # type: ignore[no-untyped-def]
    from apps.carts.models import Cart

    return Cart.objects.create(branch=branch, user=verified_user)


@pytest.fixture
def promo(db, branch):  # type: ignore[no-untyped-def]
    """10% off, capped at ₦5,000, minimum order ₦2,000."""
    from apps.promotions.models import DiscountType, PromoCode

    return PromoCode.objects.create(
        branch=branch,
        code="WELCOME10",
        discount_type=DiscountType.PERCENTAGE,
        value=1000,  # 10.00% in basis points
        max_discount=500_000,  # ₦5,000.00
        min_order_value=200_000,  # ₦2,000.00
    )


@pytest.fixture
def address(db, verified_user, zone):  # type: ignore[no-untyped-def]
    from apps.accounts.models import Address

    return Address.objects.create(
        user=verified_user,
        label="home",
        recipient_name="Ada Obi",
        phone="+2348012345678",
        street="12 Adeola Odeku Street",
        area="Victoria Island",
        city="Lagos",
        state="Lagos",
        is_default=True,
    )


@pytest.fixture
def kitchen_user(db):  # type: ignore[no-untyped-def]
    from django.contrib.auth.models import Group

    from apps.accounts.models import User

    user = User.objects.create_user(
        email="chef@kuyashplace.com", password="correct-horse-battery-staple", full_name="Chef"
    )
    user.groups.add(Group.objects.get_or_create(name="kitchen")[0])
    return user


@pytest.fixture
def manager_user(db):  # type: ignore[no-untyped-def]
    from django.contrib.auth.models import Group

    from apps.accounts.models import User

    user = User.objects.create_user(
        email="manager@kuyashplace.com",
        password="correct-horse-battery-staple",
        full_name="Manager",
    )
    user.groups.add(Group.objects.get_or_create(name="managers")[0])
    return user


@pytest.fixture
def ready_cart(db, branch, category, user_cart, address):  # type: ignore[no-untyped-def]
    """A cart that can actually be checked out: one priced item, an address."""
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem

    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Classic Smash Burger",
        slug="classic-smash-burger",
        base_price=1_090_000,
        needs_repricing=False,
        prep_time_minutes=18,
    )
    svc.add_item(cart=user_cart, item_slug="classic-smash-burger", quantity=2)
    user_cart.delivery_address = address
    user_cart.save()
    return user_cart
