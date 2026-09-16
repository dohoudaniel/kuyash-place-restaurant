"""Order placement.

The single most important path in the system. See
``docs/ARCHITECTURE.md`` §5 for the sequence this implements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.carts.models import CartStatus
from apps.carts.services.pricing import price_cart
from apps.common.exceptions import (
    BranchClosed,
    DomainError,
    ItemUnavailable,
    PriceChanged,
    PromoInvalid,
)
from apps.orders.models import (
    EventSource,
    Order,
    OrderItem,
    OrderItemModifier,
    OrderStatus,
    OrderStatusEvent,
    PaymentMethod,
    PaymentStatus,
)
from apps.orders.services.eta import estimate
from apps.orders.signals import order_placed

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EtaLine:
    """What the ETA calculation needs from a line: how long and how many."""

    prep_time_minutes: int | None
    quantity: int


class CheckoutBlocked(DomainError):
    code = "checkout_blocked"
    title = "Your order cannot be placed yet"
    status_code = 409


@transaction.atomic
def place_order(
    *,
    cart: Any,
    payment_method: str,
    expected_total: int | None = None,
    guest: dict[str, str] | None = None,
    customer_note: str = "",
    idempotency_key: str = "",
) -> Order:
    """Turn a cart into an order.

    Everything is revalidated and repriced here. The cart's totals were a quote;
    these are the charge.

    The cart is **not** cleared — that happens when payment is verified. The
    frontend clears it before anything is persisted, which makes a failure
    unrecoverable.
    """
    branch = cart.branch
    priced = price_cart(cart)

    # ── Gates ─────────────────────────────────────────────────────────────────
    if not priced.lines:
        raise CheckoutBlocked("Your cart is empty.")
    if not branch.can_accept_orders:
        raise BranchClosed("We are not accepting orders right now.")
    if payment_method == PaymentMethod.TRANSFER and not branch.accepts_bank_transfer:
        # Enforced here, not only by hiding the option: an order placed for
        # transfer with no account to pay into can never be paid.
        raise CheckoutBlocked(
            "Bank transfer isn't available right now. Please choose another way to pay."
        )

    unavailable = [line for line in priced.lines if not line.is_available]
    if unavailable:
        raise ItemUnavailable(
            "Some items are no longer available.",
            items=[line.slug for line in unavailable],
        )

    blocking = [
        blocker
        for blocker in priced.blockers
        if blocker["code"] not in {"item_unavailable", "cart_empty", "branch_closed"}
    ]
    if blocking:
        raise CheckoutBlocked(blocking[0]["detail"], blockers=blocking)

    # The price-changed guard: refuse rather than silently charge a new amount.
    if expected_total is not None and expected_total != priced.grand_total:
        from apps.common.money import format_money

        raise PriceChanged(
            "Prices changed while you were checking out. Please review and confirm.",
            expected={"amount": expected_total, "display": format_money(expected_total)},
            actual={
                "amount": priced.grand_total,
                "display": format_money(priced.grand_total),
            },
        )

    if cart.user is None and not (guest and guest.get("email")):
        raise CheckoutBlocked("An email address is required to place an order.")

    # ── Promo: claim the code before anything is written ──────────────────────
    # Two simultaneous checkouts both read ``times_used`` as 0 and both redeem a
    # ``usage_limit=1`` code. Locking the row serialises them: the loser blocks
    # until the winner's redemption is committed, then re-reads the count and is
    # refused. Claimed *before* the order row exists so that the loser writes
    # nothing at all, and so that ``first_order_only`` cannot mistake this very
    # order for the customer's order history.
    locked_promo = None
    if cart.promo_code_id is not None and priced.promo_code:
        from django.conf import settings

        from apps.promotions.models import PromoCode
        from apps.promotions.services import validate_promo

        promo_queryset = PromoCode.objects.filter(pk=cart.promo_code_id)
        if settings.USING_POSTGRES:  # pragma: no cover - exercised in Postgres CI
            # SQLite has no row locking; the surrounding transaction is the best
            # it offers, which is sufficient for local development (ADR-015).
            promo_queryset = promo_queryset.select_for_update()
        locked_promo = promo_queryset.get()

        recheck = validate_promo(
            promo=locked_promo,
            subtotal=priced.subtotal,
            user=cart.user,
            eligible_subtotal=priced.promo_eligible_subtotal,
        )
        if not recheck.ok:
            raise PromoInvalid(recheck.reason)

    # ── Address snapshot ──────────────────────────────────────────────────────
    address = cart.delivery_address
    guest = guest or {}

    order = Order(
        branch=branch,
        user=cart.user,
        # Snapshotted so that confirming payment empties *this* basket and no
        # other customer's.
        cart=cart,
        guest_email="" if cart.user else guest.get("email", ""),
        guest_phone="" if cart.user else guest.get("phone", ""),
        guest_name="" if cart.user else guest.get("full_name", ""),
        payment_method=payment_method,
        fulfilment_type=cart.fulfilment_type,
        customer_note=customer_note.strip(),
        idempotency_key=idempotency_key,
        subtotal=priced.subtotal,
        discount_total=priced.discount_total,
        delivery_fee=priced.delivery_fee,
        service_charge=priced.service_charge,
        vat_total=priced.vat_total,
        tip=priced.tip,
        grand_total=priced.grand_total,
        vat_rate_bps=priced.vat_rate_bps,
        prices_included_vat=priced.prices_include_vat,
        currency=priced.currency,
        promo_code_snapshot=priced.promo_code,
    )
    if address is not None:
        order.recipient_name = address.recipient_name
        order.recipient_phone = address.phone
        order.street = address.street
        order.area = address.area
        order.city = address.city
        order.state = address.state
        order.landmark = address.landmark
        order.delivery_notes = address.delivery_notes
        order.delivery_zone_name = address.zone.name if address.zone else ""
    elif cart.user is None:
        order.recipient_name = guest.get("full_name", "")
        order.recipient_phone = guest.get("phone", "")

    # Cash is confirmed immediately; card and transfer wait for money.
    if payment_method == PaymentMethod.CASH:
        order.status = OrderStatus.CONFIRMED
        order.payment_status = PaymentStatus.UNPAID
    else:
        order.status = OrderStatus.PENDING_PAYMENT
        order.payment_status = PaymentStatus.PENDING

    from django.utils import timezone

    order.placed_at = timezone.now()
    order.save()

    # ── Line snapshots ────────────────────────────────────────────────────────
    # Two statements rather than two per line: a ten-line order with options
    # cost around forty INSERTs on the most important path in the system.
    cart_items = {str(item.pk): item for item in cart.items.select_related("menu_item", "variant")}
    order_items = []
    for line in priced.lines:
        menu_item = cart_items[line.cart_item_id].menu_item
        order_items.append(
            OrderItem(
                order=order,
                menu_item=menu_item,
                name_snapshot=line.name,
                description_snapshot=menu_item.description,
                variant_name_snapshot=line.variant_name,
                slug_snapshot=line.slug,
                image_url_snapshot=(line.image_url or "")[:500],
                tax_class_snapshot=line.tax_class,
                unit_price=line.unit_price,
                quantity=line.quantity,
                line_subtotal=line.line_subtotal,
                line_discount=line.discount,
                line_vat=line.vat,
                special_instructions=line.special_instructions,
            )
        )
    OrderItem.objects.bulk_create(order_items)

    chosen_options = [
        OrderItemModifier(
            order_item=order_item,
            name_snapshot=modifier.name,
            price_delta=modifier.price_delta,
            quantity=modifier.quantity,
        )
        for order_item, line in zip(order_items, priced.lines, strict=True)
        for modifier in line.modifiers
    ]
    if chosen_options:
        OrderItemModifier.objects.bulk_create(chosen_options)

    # ── Promo ledger ──────────────────────────────────────────────────────────
    # Written whenever a code validated, not only when it took money off the
    # goods. ``calculate_discount`` returns 0 for a free-delivery code, so the
    # old ``and priced.promo_discount`` guard meant free-delivery codes were
    # recorded nowhere: ``times_used`` is derived from this ledger, so a
    # ``usage_limit=1`` free-delivery code was infinite-use, by everyone,
    # forever, with no audit trail.
    if locked_promo is not None:
        from apps.promotions.models import PromoRedemption, RedemptionStatus

        PromoRedemption.objects.create(
            promo_code=locked_promo,
            user=cart.user,
            order=order,
            order_reference=order.reference,
            discount_amount=priced.promo_discount,
            status=RedemptionStatus.PENDING,
        )

    # ── Loyalty reward: points are spent now, returned if the order fails ─────
    if priced.reward is not None and priced.reward["applied"]:
        from apps.loyalty.services import spend_reward_for_order

        spend_reward_for_order(cart=cart, order=order, discount=priced.reward["discount_amount"])

    # ── ETA ───────────────────────────────────────────────────────────────────
    zone_minutes = address.zone.estimated_minutes if address is not None and address.zone else None
    ready_at, delivery_at = estimate(
        branch=branch,
        items=[
            EtaLine(prep_time_minutes=item.menu_item.prep_time_minutes, quantity=item.quantity)
            for item in cart_items.values()
        ],
        fulfilment_type=cart.fulfilment_type,
        zone_minutes=zone_minutes,
    )
    order.estimated_ready_at = ready_at
    order.estimated_delivery_at = delivery_at
    order.save(update_fields=["estimated_ready_at", "estimated_delivery_at", "updated_at"])

    OrderStatusEvent.objects.create(
        order=order,
        from_status="",
        to_status=order.status,
        source=EventSource.CUSTOMER,
        actor=cart.user,
        note="Order placed.",
    )

    # Mark the cart converted. Its contents stay until payment is verified so a
    # failed payment leaves the customer's basket intact.
    cart.status = CartStatus.CONVERTED
    cart.save(update_fields=["status", "updated_at"])

    logger.info("order_placed", extra={"order": order.reference, "total": order.grand_total})
    order_placed.send(sender=Order, order=order)
    return order
