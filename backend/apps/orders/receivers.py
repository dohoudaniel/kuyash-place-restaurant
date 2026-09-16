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


#: An order in any of these states did not, in the end, feed anyone, so the
#: customer gets their promo use back. ``loyalty.receivers.UNDONE_STATUSES``
#: holds the same set for points: the two ledgers used to disagree about
#: EXPIRED and FAILED, so abandoning a payment permanently burned a
#: one-per-customer code while refunding the very same order returned it.
UNDONE_STATUSES = frozenset(
    {
        OrderStatus.REFUNDED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    }
)


@receiver(order_paid, dispatch_uid="orders.clear_cart_on_payment")
def clear_cart_on_payment(sender: type[Order], order: Order, **kwargs: Any) -> None:
    """Empty the basket this order came from — and no other (ORD-4).

    The frontend clears the cart at submit, so a failed payment loses the
    customer's basket with no way back; ``place_order`` therefore leaves a
    converted cart's items in place until the money is confirmed.

    This used to select carts by *customer identity and branch* rather than by
    the order's own cart, so paying for one order emptied every converted
    basket that matched: a guest sitting on the payment page lost their items
    when an unrelated guest paid, and a signed-in customer with two outstanding
    orders lost the basket attached to the other one.
    """
    if order.cart_id is None:
        # Orders placed before the cart was snapshotted, and any order whose
        # cart has since been purged. Nothing identifies a basket to clear, and
        # guessing is what caused the bug above.
        return

    from apps.carts.models import CartItem

    CartItem.objects.filter(cart_id=order.cart_id).delete()


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
    """Refunding, cancelling or abandoning gives the promo use back (RF-4)."""
    if to_status not in UNDONE_STATUSES:
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


def _amount_received(order: Order) -> int:
    """What was actually collected against this order, in kobo.

    A read-only query into ``payments``. ``amount_paid`` used to be set to
    ``grand_total`` regardless of what settled, which is why a duplicate charge
    could not be refunded through the API at all: refunds are capped at
    ``amount_paid``, so a second settlement's money was invisible to them.

    ``amount_verified`` is what the provider says arrived; ``amount`` is what we
    asked for, used only where the provider reported no figure. With no
    successful transaction at all — a cash order, or money recorded outside the
    system — there is nothing to derive from and the order total stands.
    """
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    from apps.payments.models import PaymentTransaction, TransactionStatus

    received = PaymentTransaction.objects.filter(
        order_id=order.pk, status=TransactionStatus.SUCCESS
    ).aggregate(total=Sum(Coalesce("amount_verified", "amount")))["total"]
    return int(received) if received is not None else order.grand_total


@receiver(order_paid, dispatch_uid="orders.mark_payment_status")
def mark_payment_status(sender: type[Order], order: Order, **kwargs: Any) -> None:
    if order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        order.amount_paid = _amount_received(order)
        order.save(update_fields=["payment_status", "amount_paid", "updated_at"])
