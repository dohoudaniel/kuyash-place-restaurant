"""Kuyash Rewards: a points ledger, tiers and rewards.

Replaces ``app/rewards/page.tsx``, where "Join Free Now" set ``signedUp = true``
in component state — refresh the page and you were not a member — beside
points, tiers, a rewards catalogue and bonuses that existed only as copy.

The ledger is the source of truth (LOY-1). ``LoyaltyAccount.points_balance`` is
a cache of its sum, updated in the same transaction as every entry.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.common.fields import MoneyField
from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class LedgerEntryType(models.TextChoices):
    EARN = "earn", "Earned"
    REDEEM = "redeem", "Redeemed"
    EXPIRE = "expire", "Expired"
    ADJUSTMENT = "adjustment", "Adjustment"
    REVERSAL = "reversal", "Reversal"


class RewardType(models.TextChoices):
    DISCOUNT = "discount", "Money off"
    FREE_DELIVERY = "free_delivery", "Free delivery"
    FREE_ITEM = "free_item", "Free dish"


class RewardRedemptionStatus(models.TextChoices):
    SPENT = "spent", "Spent on an order"
    REVERSED = "reversed", "Points returned"


class LoyaltyTier(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True)
    min_points = models.PositiveIntegerField(
        unique=True, help_text="Lifetime points needed to reach this tier."
    )
    points_multiplier_bps = models.PositiveIntegerField(
        default=10_000,
        validators=[MinValueValidator(1)],
        help_text="Basis points. 10000 = 1× the base earn rate, 15000 = 1.5×.",
    )
    birthday_points = models.PositiveIntegerField(
        default=0, help_text="Points granted on the member's birthday. 0 = none."
    )
    benefits = models.JSONField(
        default=list,
        blank=True,
        help_text="Extra perks, one per line. Only list what the restaurant actually honours.",
    )
    colour = models.CharField(
        max_length=7,
        default="#94a3b8",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a hex colour such as #eab308.")],
    )

    class Meta:
        ordering = ["min_points"]

    def __str__(self) -> str:
        return self.name


class LoyaltyAccount(TimeStampedModel):
    """Every signed-in customer has one; joining is having an account."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="loyalty_account"
    )
    points_balance = models.IntegerField(
        default=0, help_text="Cached sum of the ledger. Can go negative after a reversal."
    )
    lifetime_points = models.IntegerField(
        default=0, help_text="Points earned, net of reversed earnings. Decides the tier."
    )
    tier = models.ForeignKey(
        LoyaltyTier, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounts"
    )
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} — {self.points_balance} pts"


class Reward(TimeStampedModel, SoftDeleteModel):
    branch = models.ForeignKey("core.Branch", on_delete=models.CASCADE, related_name="rewards")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    points_cost = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reward_type = models.CharField(max_length=20, choices=RewardType.choices)
    value = MoneyField(help_text="Kobo off the order. Money-off rewards only.")
    min_order_value = MoneyField(help_text="Subtotal in kobo needed to use it. 0 = none.")
    menu_item = models.ForeignKey(
        "catalog.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewards",
        help_text="Free-dish rewards only: one of these comes off the order.",
    )
    stock = models.PositiveIntegerField(
        null=True, blank=True, help_text="How many can still be redeemed. Blank = unlimited."
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "points_cost"]

    def __str__(self) -> str:
        return f"{self.name} ({self.points_cost} pts)"

    def clean(self) -> None:
        if self.reward_type == RewardType.DISCOUNT and not self.value:
            raise ValidationError({"value": "A money-off reward needs an amount."})
        if self.reward_type == RewardType.FREE_ITEM and self.menu_item_id is None:
            raise ValidationError({"menu_item": "Choose the dish this reward gives away."})


class PointsLedgerEntry(UUIDModel):
    """One movement of points. Append-only: never updated, never deleted."""

    account = models.ForeignKey(LoyaltyAccount, on_delete=models.PROTECT, related_name="entries")
    entry_type = models.CharField(max_length=20, choices=LedgerEntryType.choices, db_index=True)
    points = models.IntegerField(
        help_text="Signed. Negative for redemptions, expiry and reversals of earnings."
    )
    description = models.CharField(max_length=200)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyalty_entries",
    )
    reward = models.ForeignKey(
        Reward, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    reversal_of = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversals"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        help_text="Stops the same event (an order, a birthday) posting twice.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "points ledger entries"

    def __str__(self) -> str:
        return f"{self.points:+d} {self.get_entry_type_display()}: {self.description}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Ledger entries are append-only. Post a reversal or adjustment.")
        super().save(*args, **kwargs)


class RewardRedemption(TimeStampedModel):
    account = models.ForeignKey(
        LoyaltyAccount, on_delete=models.PROTECT, related_name="redemptions"
    )
    reward = models.ForeignKey(Reward, on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyalty_redemption",
    )
    points_spent = models.PositiveIntegerField()
    discount_amount = MoneyField()
    status = models.CharField(
        max_length=20,
        choices=RewardRedemptionStatus.choices,
        default=RewardRedemptionStatus.SPENT,
    )
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reward.name} — {self.get_status_display()}"
