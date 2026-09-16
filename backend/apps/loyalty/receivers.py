"""Loyalty reacts to order events; orders never import loyalty (ADR-014)."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.signals import user_anonymised
from apps.core import cache as core_cache
from apps.loyalty.models import LoyaltyTier
from apps.orders.models import OrderStatus
from apps.orders.signals import order_status_changed

#: An order in any of these states did not, in the end, feed anyone.
UNDONE_STATUSES = frozenset(
    {
        OrderStatus.REFUNDED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    }
)


@receiver(order_status_changed, dispatch_uid="loyalty.points_follow_orders")
def points_follow_orders(
    sender: Any, order: Any, from_status: str, to_status: str, **kwargs: Any
) -> None:
    from apps.loyalty import services

    if to_status == OrderStatus.DELIVERED:
        services.earn_for_order(order)
    elif to_status in UNDONE_STATUSES:
        services.reverse_order(order)


@receiver(user_anonymised, dispatch_uid="loyalty.close_on_anonymise")
def close_on_anonymise(sender: Any, user: Any, **kwargs: Any) -> None:
    from apps.loyalty import services

    services.close_account(user)


@receiver(post_save, sender=LoyaltyTier, dispatch_uid="loyalty.cache.tier_saved")
@receiver(post_delete, sender=LoyaltyTier, dispatch_uid="loyalty.cache.tier_deleted")
def drop_programme_cache(sender: Any, instance: LoyaltyTier, **kwargs: Any) -> None:
    """The tiers and earning rules the public rewards page shows."""
    core_cache.invalidate(core_cache.LOYALTY_PROGRAMME_KEY)
