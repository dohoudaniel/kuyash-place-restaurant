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
    """Email the customer on the transitions they care about.

    Wording lives in editable templates; this decides only *when* to write.
    """
    from django.conf import settings

    from apps.carts.serializers import money
    from apps.notifications.services import queue_templated_email

    recipient = order.contact_email
    if not recipient:
        return

    tracking_url = f"{settings.FRONTEND_URL}/orders/{order.reference}"
    is_delivery = order.fulfilment_type == "delivery"
    assignment = getattr(order, "delivery_assignment", None)

    base = {
        "name": order.contact_name,
        "reference": order.reference,
        "tracking_url": tracking_url,
        "total": money(order.grand_total, order.currency)["display"],
    }

    if to_status == OrderStatus.PAID:
        key, extra = (
            "order_confirmation",
            {
                "fulfilment_line": (
                    f"Delivery to {order.street}, {order.city}."
                    if is_delivery
                    else "For collection from the restaurant."
                ),
            },
        )
    elif to_status == OrderStatus.PREPARING:
        eta = order.estimated_delivery_at if is_delivery else order.estimated_ready_at
        key, extra = (
            "order_accepted",
            {
                "eta_line": (
                    f"Estimated {'delivery' if is_delivery else 'ready'} time: {eta:%H:%M}."
                    if eta
                    else ""
                ),
            },
        )
    elif to_status == OrderStatus.READY and not is_delivery:
        key, extra = "order_ready", {}
    elif to_status == OrderStatus.OUT_FOR_DELIVERY:
        key, extra = (
            "order_out_for_delivery",
            {
                "rider_line": (
                    f"Your rider is {assignment.rider.user.get_short_name()} "
                    f"({assignment.rider.user.phone})."
                    if assignment
                    else ""
                ),
            },
        )
    elif to_status == OrderStatus.DELIVERED:
        key, extra = "order_delivered", {}
    elif to_status == OrderStatus.REJECTED:
        key, extra = (
            "order_rejected",
            {
                "refund_line": (
                    "Any payment will be refunded in full."
                    if order.is_paid
                    else "You have not been charged."
                ),
                "reason_line": "",
            },
        )
    elif to_status == OrderStatus.CANCELLED:
        key, extra = (
            "order_cancelled",
            {
                "refund_line": (
                    "Any payment will be refunded in full."
                    if order.is_paid
                    else "You have not been charged."
                ),
            },
        )
    else:
        return

    queue_templated_email(template_key=key, recipient=recipient, context={**base, **extra})


@receiver(order_paid, dispatch_uid="orders.mark_payment_status")
def mark_payment_status(sender: type[Order], order: Order, **kwargs: Any) -> None:
    if order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        order.amount_paid = order.grand_total
        order.save(update_fields=["payment_status", "amount_paid", "updated_at"])
