"""Promo validation and discount calculation.

Every commercial rule the frontend currently evaluates in the browser lives
here instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.common.money import apply_bps
from apps.promotions.models import DiscountType, PromoCode, RedemptionStatus

if TYPE_CHECKING:  # pragma: no cover
    pass


@dataclass(frozen=True, slots=True)
class PromoCheck:
    """The outcome of validating a code against a cart."""

    ok: bool
    reason: str = ""
    promo: PromoCode | None = None


def find_code(branch: Any, code: str) -> PromoCode | None:
    return PromoCode.objects.filter(
        branch=branch, code=code.upper().strip(), is_active=True
    ).first()


def validate_promo(
    *,
    promo: PromoCode | None,
    subtotal: int,
    user: Any = None,
    eligible_subtotal: int | None = None,
) -> PromoCheck:
    """Check whether a code may be applied.

    Reasons are deliberately generic about *existence*: an invalid code and an
    exhausted code report differently only where that is safe to disclose.
    """
    if promo is None:
        return PromoCheck(False, "That code is not valid.")

    if not promo.is_within_window:
        now = timezone.now()
        if promo.valid_until and now > promo.valid_until:
            return PromoCheck(False, "That code has expired.")
        return PromoCheck(False, "That code is not active yet.")

    if promo.usage_limit is not None and promo.times_used >= promo.usage_limit:
        return PromoCheck(False, "That code has been fully redeemed.")

    if promo.usage_limit_per_user is not None and promo.times_used_by(user) >= (
        promo.usage_limit_per_user
    ):
        return PromoCheck(False, "You have already used that code.")

    if promo.first_order_only:
        if user is None or not getattr(user, "is_authenticated", False):
            return PromoCheck(False, "That code is for first orders — please sign in.")
        used_before = (
            promo.redemptions.filter(user=user).exclude(status=RedemptionStatus.REVERSED).exists()
        )
        if used_before or has_ordered_before(user):
            return PromoCheck(False, "That code is for first orders only.")

    if subtotal < promo.min_order_value:
        from apps.common.money import format_money

        return PromoCheck(
            False, f"Spend at least {format_money(promo.min_order_value)} to use that code."
        )

    if promo.is_targeted and not eligible_subtotal:
        return PromoCheck(False, "That code does not apply to anything in your cart.")

    return PromoCheck(True, promo=promo)


def has_ordered_before(user: Any) -> bool:
    """Whether this customer has a real order behind them.

    ``first_order_only`` used to ask only whether *this code* had been redeemed,
    so a customer with two hundred orders still qualified for the new-customer
    discount. The question is about their order history, not the code's.

    Orders that were cancelled, rejected, expired or abandoned at payment never
    fed anyone, so they do not count as a first order.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    # Imported here, not at module scope: ``orders`` imports this module during
    # placement, and a top-level import would close the cycle.
    from apps.orders.models import Order, OrderStatus

    never_happened = [
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    ]
    return Order.objects.filter(user_id=user.pk).exclude(status__in=never_happened).exists()


def eligible_lines(promo: PromoCode, lines: list[Any]) -> list[bool]:
    """Which lines a code applies to, one flag per line, in order.

    The size of a targeted discount and its allocation across lines have to
    agree about *which* lines are eligible, so both are derived from here.
    """
    if not promo.is_targeted:
        return [True] * len(lines)

    category_ids = set(promo.applicable_categories.values_list("id", flat=True))
    item_ids = set(promo.applicable_items.values_list("id", flat=True))

    return [
        bool(line.menu_item.id in item_ids or line.menu_item.category_id in category_ids)
        for line in lines
    ]


def eligible_amount(promo: PromoCode, lines: list[Any]) -> int:
    """The portion of the cart a code applies to.

    An untargeted code applies to the whole subtotal; a targeted one applies
    only to matching lines.
    """
    return sum(
        line.line_subtotal
        for line, applies in zip(lines, eligible_lines(promo, lines), strict=True)
        if applies
    )


def calculate_discount(promo: PromoCode, eligible_subtotal: int) -> int:
    """The discount in kobo. Free-delivery codes discount nothing here.

    Never exceeds the eligible amount: a ₦5,000 fixed discount on a ₦3,000
    order is ₦3,000 off, not a ₦2,000 refund.
    """
    if promo.discount_type == DiscountType.FREE_DELIVERY:
        return 0
    if promo.discount_type == DiscountType.PERCENTAGE:
        return apply_bps(eligible_subtotal, promo.value, cap=promo.max_discount)
    return min(promo.value, eligible_subtotal)


__all__ = [
    "PromoCheck",
    "calculate_discount",
    "eligible_amount",
    "eligible_lines",
    "find_code",
    "has_ordered_before",
    "validate_promo",
]
