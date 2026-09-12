"""Promo codes and their redemption ledger.

Replaces ``frontend/lib/store/promoStore.ts``, which ships every code, its type,
value, minimum order, cap, expiry and usage limit to the browser in the JS
bundle — and lists them to the customer.
"""

from __future__ import annotations

from typing import Any

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.common.fields import MoneyField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch


class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage off"
    FIXED = "fixed", "Fixed amount off"
    FREE_DELIVERY = "free_delivery", "Free delivery"


class RedemptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    REVERSED = "reversed", "Reversed"


class PromoCode(TimeStampedModel, SoftDeleteModel):
    """A discount code.

    Codes live here and are validated server-side. Nothing about a code —
    neither its existence nor its rules — is ever sent to a client that has not
    successfully applied it.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="promo_codes")
    code = models.CharField(max_length=32, db_index=True)
    description = models.CharField(max_length=255, blank=True)

    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(10_000)],
        help_text=(
            "For a percentage: basis points (1000 = 10%). "
            "For a fixed amount: kobo. Ignored for free delivery."
        ),
    )

    min_order_value = MoneyField(help_text="Minimum subtotal in kobo for the code to apply.")
    max_discount = MoneyField(
        null=True, blank=True, help_text="Caps a percentage discount, in kobo. Blank = uncapped."
    )

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)

    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total redemptions allowed across all customers."
    )
    usage_limit_per_user = models.PositiveIntegerField(
        null=True, blank=True, help_text="Redemptions allowed per customer."
    )
    first_order_only = models.BooleanField(default=False)

    applicable_categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="promo_codes",
        help_text="Leave empty to apply to the whole order.",
    )
    applicable_items = models.ManyToManyField(
        "catalog.MenuItem",
        blank=True,
        related_name="promo_codes",
        help_text="Leave empty to apply to the whole order.",
    )

    is_public = models.BooleanField(
        default=False,
        help_text=(
            "Whether this code may ever be listed to customers. Default off: the "
            "current frontend enumerates every available code to the user."
        ),
    )

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="unique_promo_code_per_branch")
        ]

    def __str__(self) -> str:
        return self.code

    def save(self, *args: object, **kwargs: object) -> None:
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @property
    def is_within_window(self) -> bool:
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        return not (self.valid_until and now > self.valid_until)

    @property
    def times_used(self) -> int:
        """Live count from the ledger.

        Derived, never stored: the frontend's ``usedCount`` is a number in a
        JavaScript object that resets on page refresh.
        """
        return self.redemptions.filter(
            status__in=[RedemptionStatus.PENDING, RedemptionStatus.CONFIRMED]
        ).count()

    def times_used_by(self, user: Any | None) -> int:
        """Redemptions by one customer.

        Anonymous callers have no history, so a per-user limit cannot bind them —
        which is why ``first_order_only`` additionally requires signing in.
        """
        if user is None or not getattr(user, "is_authenticated", False):
            return 0
        return self.redemptions.filter(
            user_id=user.pk, status__in=[RedemptionStatus.PENDING, RedemptionStatus.CONFIRMED]
        ).count()

    @property
    def is_targeted(self) -> bool:
        """Whether the code applies to specific items rather than the whole order."""
        return self.applicable_categories.exists() or self.applicable_items.exists()


class PromoRedemption(TimeStampedModel):
    """One use of a promo code.

    The ledger is what makes ``usage_limit`` enforceable and reversible. A
    denormalised counter alone cannot be reversed correctly when an order is
    refunded.

    Both the foreign key and the denormalised reference are kept: the key
    enforces integrity, the string keeps support lookups cheap.
    """

    promo_code = models.ForeignKey(PromoCode, on_delete=models.PROTECT, related_name="redemptions")
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_redemptions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promo_redemptions",
    )
    order_reference = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Denormalised order reference, kept so support lookups stay cheap.",
    )
    discount_amount = MoneyField(help_text="Discount granted, in kobo.")
    status = models.CharField(
        max_length=20, choices=RedemptionStatus.choices, default=RedemptionStatus.PENDING
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["promo_code", "status"])]

    def __str__(self) -> str:
        return f"{self.promo_code.code} — {self.status}"
