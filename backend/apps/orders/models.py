"""Orders.

An order is a **snapshot**, not a set of live joins. Editing an address or
raising a price must never rewrite what a customer already agreed to pay.
"""

from __future__ import annotations

import secrets
import uuid

from django.db import models

from apps.common.fields import MoneyField, PhoneField, SignedMoneyField
from apps.common.models import TimeStampedModel
from apps.core.models import Branch

# No 0/O or 1/I: an order reference gets read aloud over the phone.
REFERENCE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
REFERENCE_LENGTH = 6
REFERENCE_PREFIX = "KYS-"


def generate_reference() -> str:
    """A random, non-sequential order reference.

    32**6 ≈ 1.07 billion values. Contrast with the frontend's
    ``KYS-${Date.now().toString(36).toUpperCase()}``, which is client-generated,
    ordered, collision-prone between concurrent users, and leaks order timing.
    """
    for _ in range(12):
        candidate = REFERENCE_PREFIX + "".join(
            secrets.choice(REFERENCE_ALPHABET) for _ in range(REFERENCE_LENGTH)
        )
        if not Order.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Could not allocate an order reference.")  # pragma: no cover


def generate_guest_token() -> str:
    return secrets.token_urlsafe(32)


class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Awaiting payment"
    PAID = "paid", "Paid"
    CONFIRMED = "confirmed", "Confirmed by the kitchen"
    PREPARING = "preparing", "Preparing"
    READY = "ready", "Ready"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
    DELIVERED = "delivered", "Delivered"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    FAILED_DELIVERY = "failed_delivery", "Delivery failed"
    REFUNDED = "refunded", "Refunded"
    FAILED = "failed", "Failed"


class PaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"
    REFUNDED = "refunded", "Refunded"
    FAILED = "failed", "Failed"


class PaymentMethod(models.TextChoices):
    CARD = "card", "Card"
    TRANSFER = "transfer", "Bank transfer"
    CASH = "cash", "Cash on delivery"


class EventSource(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    STAFF = "staff", "Staff"
    SYSTEM = "system", "System"
    WEBHOOK = "webhook", "Webhook"


class Order(TimeStampedModel):
    """A placed order."""

    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="orders")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    guest_email = models.EmailField(blank=True)
    guest_phone = PhoneField(blank=True)
    guest_name = models.CharField(max_length=150, blank=True)
    guest_token = models.CharField(
        max_length=64,
        blank=True,
        default=generate_guest_token,
        help_text="Lets a guest read and cancel this one order. Scoped to it alone.",
    )

    status = models.CharField(
        max_length=24,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=24, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    fulfilment_type = models.CharField(max_length=20, default="delivery")

    # ── Address snapshot: copied, never a foreign key (ORD-3) ─────────────────
    recipient_name = models.CharField(max_length=150, blank=True)
    recipient_phone = PhoneField(blank=True)
    street = models.CharField(max_length=255, blank=True)
    area = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    delivery_notes = models.TextField(blank=True)
    delivery_zone_name = models.CharField(max_length=120, blank=True)

    # ── Money snapshot ────────────────────────────────────────────────────────
    subtotal = MoneyField()
    discount_total = MoneyField()
    delivery_fee = MoneyField()
    service_charge = MoneyField()
    vat_total = MoneyField()
    tip = MoneyField()
    grand_total = MoneyField()
    amount_paid = MoneyField()

    vat_rate_bps = models.PositiveIntegerField(
        default=750, help_text="The rate at the time of the order, not today's."
    )
    prices_included_vat = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default="NGN")
    promo_code_snapshot = models.CharField(max_length=32, blank=True)

    placed_at = models.DateTimeField(null=True, blank=True)
    estimated_ready_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    cancellation_reason = models.TextField(blank=True)
    customer_note = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)

    cart = models.ForeignKey(
        "carts.Cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text=(
            "The basket this order was placed from, so confirming payment "
            "empties that basket and no other customer's."
        ),
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            # Every report and the KDS summary range-filter on placed_at.
            models.Index(fields=["branch", "placed_at"]),
            # The KDS queue filters on branch and status and sorts on
            # placed_at; without this it filtered on one index and sorted on
            # another.
            models.Index(fields=["branch", "status", "placed_at"]),
        ]
        constraints = [
            # The durable backstop behind the idempotency cache: if the cache is
            # evicted or a second worker races the claim, the database still
            # refuses a second order for the same key. Partial, so the blank
            # default on older rows cannot collide.
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_order_idempotency_key",
            )
        ]

    def __str__(self) -> str:
        return self.reference

    @property
    def contact_email(self) -> str:
        return self.user.email if self.user else self.guest_email

    @property
    def contact_name(self) -> str:
        if self.recipient_name:
            return self.recipient_name
        return self.user.get_short_name() if self.user else (self.guest_name or "there")

    @property
    def is_paid(self) -> bool:
        return self.payment_status == PaymentStatus.PAID

    @property
    def can_cancel(self) -> bool:
        """Customers may cancel until the kitchen starts cooking (ORD-10)."""
        return self.status in {OrderStatus.PENDING_PAYMENT, OrderStatus.PAID, OrderStatus.CONFIRMED}


class OrderItem(models.Model):
    """A line, fully snapshotted.

    ``menu_item`` is kept only for analytics and is nulled if the dish is ever
    deleted; every value a customer saw is stored here verbatim.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "catalog.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )

    #: The id clients see. The integer primary key never leaves the server.
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    name_snapshot = models.CharField(max_length=150)
    description_snapshot = models.TextField(blank=True)
    variant_name_snapshot = models.CharField(max_length=80, blank=True)
    slug_snapshot = models.SlugField(max_length=160, blank=True)
    image_url_snapshot = models.URLField(blank=True, max_length=500)
    tax_class_snapshot = models.CharField(max_length=20, default="standard")

    unit_price = MoneyField()
    quantity = models.PositiveSmallIntegerField(default=1)
    line_subtotal = MoneyField()
    line_discount = MoneyField()
    line_vat = MoneyField()
    special_instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.name_snapshot}"


class OrderItemModifier(models.Model):
    """A chosen option, snapshotted with the price it carried."""

    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="modifiers")
    name_snapshot = models.CharField(max_length=120)
    price_delta = SignedMoneyField()
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name_snapshot


class OrderStatusEvent(models.Model):
    """Append-only audit of every status change.

    Never updated, never deleted. This is what answers "who marked it delivered
    and when" when a customer disputes an order, and it is the ETag source for
    cheap polling.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_events",
    )
    actor_role = models.CharField(max_length=40, blank=True)
    source = models.CharField(
        max_length=20, choices=EventSource.choices, default=EventSource.SYSTEM
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.order.reference}: {self.from_status} → {self.to_status}"
