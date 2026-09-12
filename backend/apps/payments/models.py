"""Payment records.

**There is no field in this module for a card number, expiry or CVV, and there
never will be.** Card data is entered on the provider's hosted checkout and
never reaches our infrastructure. What we keep is a provider reference, an
amount, and — for display only — the last four digits and brand the provider
hands back. See ``docs/PAYMENTS.md`` §1.
"""

from __future__ import annotations

from django.db import models

from apps.common.fields import MoneyField
from apps.common.models import TimeStampedModel


class Provider(models.TextChoices):
    PAYSTACK = "paystack", "Paystack"
    FLUTTERWAVE = "flutterwave", "Flutterwave"
    BANK_TRANSFER = "bank_transfer", "Bank transfer"
    CASH = "cash", "Cash"


class TransactionStatus(models.TextChoices):
    INITIALISED = "initialised", "Initialised"
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    ABANDONED = "abandoned", "Abandoned"
    REVERSED = "reversed", "Reversed"


class RefundStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class PaymentTransaction(TimeStampedModel):
    """One attempt to collect money for an order."""

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="transactions")
    provider = models.CharField(max_length=20, choices=Provider.choices)

    our_reference = models.CharField(
        max_length=64,
        unique=True,
        help_text="What we send to the provider. Derived from the order reference.",
    )
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)

    amount = MoneyField(help_text="Amount we expect, in kobo.")
    amount_verified = MoneyField(
        null=True, blank=True, help_text="What the provider says was actually paid, in kobo."
    )
    currency = models.CharField(max_length=3, default="NGN")

    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.INITIALISED,
        db_index=True,
    )
    channel = models.CharField(
        max_length=40, blank=True, help_text="card, bank, ussd, qr — as reported by the provider."
    )

    # Display-only card metadata. A reusable token, never a PAN.
    authorization_code = models.CharField(
        max_length=120,
        blank=True,
        help_text="Provider token for repeat charges. Not a card number.",
    )
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=30, blank=True)
    card_exp_month = models.CharField(max_length=2, blank=True)
    card_exp_year = models.CharField(max_length=4, blank=True)

    authorization_url = models.URLField(blank=True, max_length=500)
    raw_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    initialised_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "initialised_at"])]

    def __str__(self) -> str:
        return f"{self.our_reference} ({self.status})"

    @property
    def is_settled(self) -> bool:
        return self.status == TransactionStatus.SUCCESS


class WebhookEvent(TimeStampedModel):
    """Every inbound webhook, valid or not.

    ``event_id`` is unique: that constraint *is* the idempotency guard.
    Providers retry, and a duplicate delivery must not credit an order twice.
    """

    provider = models.CharField(max_length=20, choices=Provider.choices)
    event_id = models.CharField(max_length=160)
    event_type = models.CharField(max_length=80, blank=True)
    signature_valid = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    remote_addr = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"], name="unique_webhook_event_per_provider"
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id}"


class Refund(TimeStampedModel):
    """Money returned to a customer."""

    transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.PROTECT, related_name="refunds", null=True, blank=True
    )
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="refunds")
    amount = MoneyField(help_text="Amount refunded, in kobo.")
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=RefundStatus.choices, default=RefundStatus.PENDING
    )
    provider_reference = models.CharField(max_length=120, blank=True)
    initiated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunds_initiated",
    )
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Refund {self.amount} on {self.order.reference}"
