"""Promo code rules.

Every one of these is currently evaluated in the browser from a list shipped in
the JS bundle, where `usedCount` resets on page refresh.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.promotions.models import DiscountType, PromoCode, PromoRedemption, RedemptionStatus
from apps.promotions.services import calculate_discount, find_code, validate_promo

pytestmark = pytest.mark.django_db


def check(promo, subtotal=1_000_000, user=None, eligible=None):  # type: ignore[no-untyped-def]
    return validate_promo(
        promo=promo,
        subtotal=subtotal,
        user=user,
        eligible_subtotal=subtotal if eligible is None else eligible,
    )


def test_a_valid_code_passes(promo: PromoCode) -> None:
    assert check(promo).ok is True


def test_an_unknown_code_is_refused(branch) -> None:  # type: ignore[no-untyped-def]
    assert find_code(branch, "NOPE") is None
    assert check(None).ok is False


def test_codes_are_matched_case_insensitively(branch, promo: PromoCode) -> None:  # type: ignore[no-untyped-def]
    assert find_code(branch, "welcome10") == promo
    assert find_code(branch, "  WeLcOmE10  ") == promo


def test_an_expired_code_is_refused(promo: PromoCode) -> None:
    promo.valid_until = timezone.now() - dt.timedelta(days=1)
    promo.save()
    result = check(promo)
    assert result.ok is False
    assert "expired" in result.reason


def test_a_future_code_is_refused(promo: PromoCode) -> None:
    promo.valid_from = timezone.now() + dt.timedelta(days=1)
    promo.save()
    assert check(promo).ok is False


def test_a_deactivated_code_is_not_found(branch, promo: PromoCode) -> None:  # type: ignore[no-untyped-def]
    promo.is_active = False
    promo.save()
    assert find_code(branch, "WELCOME10") is None


def test_below_the_minimum_order_is_refused(promo: PromoCode) -> None:
    result = check(promo, subtotal=100_000)  # ₦1,000 against a ₦2,000 minimum
    assert result.ok is False
    assert "₦2,000.00" in result.reason


def test_a_global_usage_limit_is_enforced(promo: PromoCode) -> None:
    """The ledger makes this real. `usedCount` in a JS object does not."""
    promo.usage_limit = 1
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo, discount_amount=100_000, status=RedemptionStatus.CONFIRMED
    )
    result = check(promo)
    assert result.ok is False
    assert "fully redeemed" in result.reason


def test_a_reversed_redemption_frees_the_allowance(promo: PromoCode) -> None:
    """Refunding an order must give the customer their use back."""
    promo.usage_limit = 1
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo, discount_amount=100_000, status=RedemptionStatus.REVERSED
    )
    assert check(promo).ok is True


def test_a_per_user_limit_is_enforced(promo: PromoCode, verified_user) -> None:  # type: ignore[no-untyped-def]
    promo.usage_limit_per_user = 1
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo,
        user=verified_user,
        discount_amount=100_000,
        status=RedemptionStatus.CONFIRMED,
    )
    result = check(promo, user=verified_user)
    assert result.ok is False
    assert "already used" in result.reason


def test_a_per_user_limit_does_not_affect_other_users(  # type: ignore[no-untyped-def]
    promo: PromoCode, verified_user, db
) -> None:
    from apps.accounts.models import User

    other = User.objects.create_user(email="other@example.com", password="correct-horse-staple-x")
    promo.usage_limit_per_user = 1
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo,
        user=verified_user,
        discount_amount=100_000,
        status=RedemptionStatus.CONFIRMED,
    )
    assert check(promo, user=other).ok is True


def test_first_order_only_requires_signing_in(promo: PromoCode) -> None:
    promo.first_order_only = True
    promo.save()
    result = check(promo, user=None)
    assert result.ok is False
    assert "sign in" in result.reason


def test_first_order_only_refuses_a_returning_customer(promo, verified_user) -> None:  # type: ignore[no-untyped-def]
    promo.first_order_only = True
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo,
        user=verified_user,
        discount_amount=100_000,
        status=RedemptionStatus.CONFIRMED,
    )
    assert check(promo, user=verified_user).ok is False


def test_a_targeted_code_needs_matching_items(promo, category) -> None:  # type: ignore[no-untyped-def]
    promo.save()
    promo.applicable_categories.add(category)
    result = check(promo, eligible=0)
    assert result.ok is False
    assert "does not apply" in result.reason


# ── Discount calculation ──────────────────────────────────────────────────────


def test_percentage_discount(promo: PromoCode) -> None:
    assert calculate_discount(promo, 1_000_000) == 100_000


def test_percentage_discount_is_capped(promo: PromoCode) -> None:
    assert calculate_discount(promo, 100_000_000) == 500_000


def test_fixed_discount(branch) -> None:  # type: ignore[no-untyped-def]
    code = PromoCode.objects.create(
        branch=branch, code="FLAT500", discount_type=DiscountType.FIXED, value=500_000
    )
    assert calculate_discount(code, 1_000_000) == 500_000


def test_a_fixed_discount_never_exceeds_the_order(branch) -> None:  # type: ignore[no-untyped-def]
    """₦5,000 off a ₦3,000 order is ₦3,000 off, not a ₦2,000 refund."""
    code = PromoCode.objects.create(
        branch=branch, code="FLAT5000", discount_type=DiscountType.FIXED, value=500_000
    )
    assert calculate_discount(code, 300_000) == 300_000


def test_free_delivery_discounts_nothing_from_the_goods(branch) -> None:  # type: ignore[no-untyped-def]
    code = PromoCode.objects.create(
        branch=branch, code="FREESHIP", discount_type=DiscountType.FREE_DELIVERY
    )
    assert calculate_discount(code, 1_000_000) == 0


def test_usage_count_is_derived_from_the_ledger(promo: PromoCode) -> None:
    assert promo.times_used == 0
    PromoRedemption.objects.create(
        promo_code=promo, discount_amount=1, status=RedemptionStatus.PENDING
    )
    PromoRedemption.objects.create(
        promo_code=promo, discount_amount=1, status=RedemptionStatus.CONFIRMED
    )
    PromoRedemption.objects.create(
        promo_code=promo, discount_amount=1, status=RedemptionStatus.REVERSED
    )
    assert promo.times_used == 2  # reversed does not count


def test_codes_are_normalised_to_uppercase(branch) -> None:  # type: ignore[no-untyped-def]
    code = PromoCode.objects.create(
        branch=branch, code="  lower10 ", discount_type=DiscountType.FIXED, value=1
    )
    assert code.code == "LOWER10"


# ── First-order-only, against the real order history ──────────────────────────


def order_for(user, branch, status):  # type: ignore[no-untyped-def]
    from apps.orders.models import Order

    return Order.objects.create(
        branch=branch, user=user, payment_method="card", grand_total=1_000_000, status=status
    )


def test_first_order_only_refuses_a_customer_who_has_ordered_before(  # type: ignore[no-untyped-def]
    promo, verified_user, branch
) -> None:
    """It used to ask only whether *this code* had been redeemed, so a customer
    with two hundred orders behind them still qualified for the new-customer
    discount."""
    from apps.orders.models import OrderStatus

    promo.first_order_only = True
    promo.save()
    order_for(verified_user, branch, OrderStatus.DELIVERED)

    result = check(promo, user=verified_user)
    assert result.ok is False
    assert "first orders only" in result.reason


def test_first_order_only_ignores_orders_that_never_happened(  # type: ignore[no-untyped-def]
    promo, verified_user, branch
) -> None:
    """A cancelled, rejected, expired or failed order fed nobody; it is not a
    first order."""
    from apps.orders.models import OrderStatus

    promo.first_order_only = True
    promo.save()
    for status in (
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    ):
        order_for(verified_user, branch, status)

    assert check(promo, user=verified_user).ok is True


def test_a_reversed_redemption_does_not_burn_first_order_only(promo, verified_user) -> None:  # type: ignore[no-untyped-def]
    """Refunding the order gave the use back everywhere else; here it did not."""
    promo.first_order_only = True
    promo.save()
    PromoRedemption.objects.create(
        promo_code=promo,
        user=verified_user,
        discount_amount=100_000,
        status=RedemptionStatus.REVERSED,
    )

    assert check(promo, user=verified_user).ok is True


@pytest.mark.parametrize("user", [None, AnonymousUser()])
def test_a_guest_has_no_order_history(user) -> None:  # type: ignore[no-untyped-def]
    """A first-order-only code cannot bind someone with no account.

    Answering False here (rather than True) keeps the code unusable by guests,
    which is what `validate_promo` relies on.
    """
    from apps.promotions.services import has_ordered_before

    assert has_ordered_before(user) is False
