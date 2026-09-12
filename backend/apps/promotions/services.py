"""Promo validation and discount calculation.

Every commercial rule the frontend currently evaluates in the browser lives
here instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.common.money import apply_bps
from apps.promotions.models import DiscountType, PromoCode

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
        if promo.redemptions.filter(user=user).exists():
            return PromoCheck(False, "That code is for first orders only.")

    if subtotal < promo.min_order_value:
        from apps.common.money import format_money

        return PromoCheck(
            False, f"Spend at least {format_money(promo.min_order_value)} to use that code."
        )

    if promo.is_targeted and not eligible_subtotal:
        return PromoCheck(False, "That code does not apply to anything in your cart.")

    return PromoCheck(True, promo=promo)


def eligible_amount(promo: PromoCode, lines: list[Any]) -> int:
    """The portion of the cart a code applies to.

    An untargeted code applies to the whole subtotal; a targeted one applies
    only to matching lines.
    """
    if not promo.is_targeted:
        return sum(line.line_subtotal for line in lines)

    category_ids = set(promo.applicable_categories.values_list("id", flat=True))
    item_ids = set(promo.applicable_items.values_list("id", flat=True))

    total = 0
    for line in lines:
        item = line.menu_item
        if item.id in item_ids or item.category_id in category_ids:
            total += line.line_subtotal
    return total


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
    "find_code",
    "validate_promo",
]
