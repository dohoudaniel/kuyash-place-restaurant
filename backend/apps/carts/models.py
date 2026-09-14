"""Server-side cart.

The frontend's cart lives in ``localStorage`` and prices itself in the browser.
This one is authoritative: nothing a client sends can change what anything costs.
"""

from __future__ import annotations

import datetime as dt
import secrets

from django.db import models
from django.utils import timezone

from apps.common.fields import MoneyField
from apps.common.models import TimeStampedModel
from apps.core.models import Branch

CART_TTL = dt.timedelta(days=30)


class CartStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CONVERTED = "converted", "Converted to an order"
    ABANDONED = "abandoned", "Abandoned"


class FulfilmentType(models.TextChoices):
    DELIVERY = "delivery", "Delivery"
    PICKUP = "pickup", "Pickup"


def generate_cart_token() -> str:
    return secrets.token_urlsafe(32)


class Cart(TimeStampedModel):
    """A basket belonging to a signed-in user or an anonymous session."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="carts")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="carts"
    )
    session_token = models.CharField(
        max_length=64,
        db_index=True,
        default=generate_cart_token,
        help_text="Identifies an anonymous cart. Sent by the client as X-Cart-Token.",
    )

    status = models.CharField(
        max_length=20, choices=CartStatus.choices, default=CartStatus.ACTIVE, db_index=True
    )
    fulfilment_type = models.CharField(
        max_length=20, choices=FulfilmentType.choices, default=FulfilmentType.DELIVERY
    )
    delivery_address = models.ForeignKey(
        "accounts.Address", on_delete=models.SET_NULL, null=True, blank=True, related_name="carts"
    )

    promo_code = models.ForeignKey(
        "promotions.PromoCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
        help_text="Applied but not yet redeemed.",
    )
    loyalty_reward = models.ForeignKey(
        "loyalty.Reward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
        help_text="Applied to the cart; the points are spent when the order is placed.",
    )
    tip = MoneyField(help_text="Gratuity in kobo. Not subject to VAT.")

    expires_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "branch"],
                condition=models.Q(status="active", user__isnull=False),
                name="one_active_cart_per_user_per_branch",
            )
        ]

    def __str__(self) -> str:
        owner = self.user.email if self.user else f"guest:{self.session_token[:8]}"
        return f"Cart<{owner}, {self.items.count()} items>"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.pk or self.status == CartStatus.ACTIVE:
            self.expires_at = timezone.now() + CART_TTL
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @property
    def is_empty(self) -> bool:
        return not self.items.exists()


class CartItem(TimeStampedModel):
    """One configured line.

    ``menu_item`` is a foreign key, not a string. The frontend keys cart items on
    ``imageKey || slugify(name)``, so renaming a dish silently orphans every
    cart row that referenced it.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "catalog.MenuItem", on_delete=models.PROTECT, related_name="cart_items"
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.PositiveSmallIntegerField(default=1)
    special_instructions = models.TextField(blank=True)

    unit_price_snapshot = MoneyField(
        help_text="Unit price when the line was last touched. Used to detect price changes.",
    )

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="cart_quantity_positive"
            )
        ]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.menu_item.name}"


class CartItemModifier(models.Model):
    """A chosen option on a line, with its own price effect."""

    cart_item = models.ForeignKey(CartItem, on_delete=models.CASCADE, related_name="modifiers")
    modifier = models.ForeignKey(
        "catalog.Modifier", on_delete=models.PROTECT, related_name="cart_item_modifiers"
    )
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["modifier__display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart_item", "modifier"], name="unique_modifier_per_cart_item"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="cart_modifier_quantity_positive"
            ),
        ]

    def __str__(self) -> str:
        return self.modifier.name
