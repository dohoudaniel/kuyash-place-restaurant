"""Reactions to order events.

These live in ``orders`` for Phase 1D because the consuming apps are thin. When
loyalty and reviews arrive in Phase 3 they will subscribe from their own
packages, and this module will shrink.
"""

from __future__ import annotations

import logging
from typing import Any

from django.dispatch import receiver

from apps.orders.models import Order, OrderStatus, PaymentStatus
from apps.orders.signals import order_paid, order_status_changed

logger = logging.getLogger(__name__)


@receiver(order_paid, dispatch_uid="orders.clear_cart_on_payment")
def clear_cart_on_payment(sender: type[Order], order: Order, **kwargs: Any) -> None:
    """Empty the basket once the money is confirmed — not before (ORD-4).

    The frontend clears the cart at submit, so a failed payment loses the
    customer's basket with no way back.
    """
    from apps.carts.models import Cart, CartStatus

    carts = Cart.objects.filter(status=CartStatus.CONVERTED)
    if order.user_id:
        carts = carts.filter(user_id=order.user_id)
    else:
        carts = carts.filter(user__isnull=True)
    for cart in carts.filter(branch=order.branch):
        cart.items.all().delete()


@receiver(order_paid, dispatch_uid="orders.confirm_promo_redemption")
def confirm_promo_redemption(sender: type[Order], order: Order, **kwargs: Any) -> None:
    """A pending redemption becomes confirmed once the order is paid."""
    from apps.promotions.models import PromoRedemption, RedemptionStatus

    PromoRedemption.objects.filter(
        order_reference=order.reference, status=RedemptionStatus.PENDING
    ).update(status=RedemptionStatus.CONFIRMED)


@receiver(order_status_changed, dispatch_uid="orders.reverse_promo_on_refund")
def reverse_promo_on_refund(
    sender: type[Order], order: Order, from_status: str, to_status: str, **kwargs: Any
) -> None:
    """Refunding or cancelling gives the customer their promo use back (RF-4)."""
    if to_status not in {OrderStatus.REFUNDED, OrderStatus.CANCELLED, OrderStatus.REJECTED}:
        return
    from apps.promotions.models import PromoRedemption, RedemptionStatus

    PromoRedemption.objects.filter(order_reference=order.reference).exclude(
        status=RedemptionStatus.REVERSED
    ).update(status=RedemptionStatus.REVERSED)


@receiver(order_status_changed, dispatch_uid="orders.count_delivered_items")
def count_delivered_items(
    sender: type[Order], order: Order, from_status: str, to_status: str, **kwargs: Any
) -> None:
    """Increment popularity counters so "sort by popular" reflects real sales."""
    if to_status != OrderStatus.DELIVERED:
        return
    from django.db.models import F

    from apps.catalog.models import MenuItem

    for line in order.items.all():
        if line.menu_item_id:
            MenuItem.objects.filter(pk=line.menu_item_id).update(
                order_count=F("order_count") + line.quantity
            )


@receiver(order_status_changed, dispatch_uid="orders.notify_customer")
def notify_customer(
    sender: type[Order], order: Order, from_status: str, to_status: str, **kwargs: Any
) -> None:
    """Email the customer on the transitions they care about."""
    from apps.notifications.services import queue_email

    templates: dict[str, tuple[str, str, str]] = {
        OrderStatus.PAID: (
            "order_confirmation",
            f"Order {order.reference} confirmed",
            "Thank you — we have your payment and the kitchen has your order.",
        ),
        OrderStatus.OUT_FOR_DELIVERY: (
            "order_out_for_delivery",
            f"Order {order.reference} is on the way",
            "Your order has left the restaurant.",
        ),
        OrderStatus.DELIVERED: (
            "order_delivered",
            f"Order {order.reference} delivered",
            "Enjoy your meal. We would love to hear how it was.",
        ),
        OrderStatus.REJECTED: (
            "order_rejected",
            f"Order {order.reference} could not be fulfilled",
            "We are sorry — the kitchen could not take this order. Any payment will be refunded.",
        ),
    }
    entry = templates.get(to_status)
    recipient = order.contact_email
    if entry is None or not recipient:
        return

    key, subject, body = entry
    queue_email(
        template_key=key,
        recipient=recipient,
        subject=subject,
        body=f"Hello {order.contact_name},\n\n{body}\n\nReference: {order.reference}\n",
        context={"order": order.reference},
    )


@receiver(order_paid, dispatch_uid="orders.mark_payment_status")
def mark_payment_status(sender: type[Order], order: Order, **kwargs: Any) -> None:
    if order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        order.amount_paid = order.grand_total
        order.save(update_fields=["payment_status", "amount_paid", "updated_at"])
