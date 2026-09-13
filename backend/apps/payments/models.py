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
    """One attempt to collect money — for an order, or for a course enrolment.

    Exactly one of ``order`` and ``enrolment`` is set (ACA-5: courses use the
    same payment infrastructure as orders, not a second one).
    """

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    enrolment = models.ForeignKey(
        "academy.Enrolment",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
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

    save_method = models.BooleanField(
        default=False,
        help_text=(
            "Whether the customer asked us to keep this card for next time. "
            "A provider returns a reusable token either way; we only persist one "
            "when this is set."
        ),
    )

    authorization_url = models.URLField(blank=True, max_length=500)
    raw_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    initialised_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "initialised_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(order__isnull=False, enrolment__isnull=True)
                    | models.Q(order__isnull=True, enrolment__isnull=False)
                ),
                name="transaction_pays_for_exactly_one_thing",
            )
        ]

    def __str__(self) -> str:
        return f"{self.our_reference} ({self.status})"

    @property
    def payable_reference(self) -> str:
        payable = self.order or self.enrolment
        return payable.reference if payable else ""

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


class SavedPaymentMethod(TimeStampedModel):
    """A card the customer chose to keep for next time.

    **This is a provider token, not a card.** ``authorization_code`` is an
    opaque string the provider will accept for a repeat charge; the last four
    digits and brand exist only so the customer can tell one saved card from
    another. There is no PAN, no expiry-as-secret and no CVV — storing a CVV is
    prohibited outright by PCI-DSS Req. 3.2, and we could not store one if we
    wanted to because we never receive it.

    Replaces ``PaymentMethodsSection.tsx``, which hardcodes a Visa •4242 and a
    Mastercard •5555 and shows them to every visitor.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="payment_methods"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    authorization_code = models.CharField(
        max_length=120, help_text="Provider token for a repeat charge. Not a card number."
    )

    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=30, blank=True)
    card_exp_month = models.CharField(max_length=2, blank=True)
    card_exp_year = models.CharField(max_length=4, blank=True)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "authorization_code"], name="unique_saved_method_per_user"
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True, is_active=True),
                name="one_default_payment_method_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.card_brand or self.provider} ••••{self.card_last4}"

    @property
    def label(self) -> str:
        return (
            f"{self.card_brand or 'Card'} ending {self.card_last4}"
            if self.card_last4
            else (self.get_provider_display())
        )

    @property
    def is_expired(self) -> bool:
        """Whether the card's own expiry has passed.

        Display only — the provider is the authority on whether a token still
        works, and a token can stop working for reasons that have nothing to do
        with the printed expiry.
        """
        if not (self.card_exp_month and self.card_exp_year):
            return False
        import datetime as dt

        try:
            month, year = int(self.card_exp_month), int(self.card_exp_year)
        except ValueError:  # pragma: no cover - defensive
            return False
        if year < 100:
            year += 2000
        today = dt.date.today()
        return (year, month) < (today.year, today.month)
