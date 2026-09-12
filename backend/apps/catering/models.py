"""Catering packages and enquiries.

Replaces ``app/catering/page.tsx:89``, where a ₦1.2M–₦6M enquiry is answered
with ``alert("Thank you! We'll contact you within 24 hours…")`` and then
``console.log``. The app promises a callback that no human is ever prompted to
make.
"""

from __future__ import annotations

import datetime as dt
import secrets

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.fields import MoneyField, PhoneField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch

#: What the site promises. The SLA the admin measures against.
RESPONSE_SLA = dt.timedelta(hours=24)

ENQUIRY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_reference() -> str:
    for _ in range(12):
        candidate = "CAT-" + "".join(secrets.choice(ENQUIRY_ALPHABET) for _ in range(6))
        if not CateringEnquiry.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Could not allocate a catering reference.")  # pragma: no cover


class EnquiryStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUOTED = "quoted", "Quoted"
    WON = "won", "Won"
    LOST = "lost", "Lost"


#: Statuses where the customer is still waiting on us.
AWAITING_RESPONSE = (EnquiryStatus.NEW,)


class CateringPackage(TimeStampedModel, SoftDeleteModel):
    """A catering tier."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="catering_packages")
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    description = models.TextField(blank=True)

    min_guests = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    max_guests = models.PositiveIntegerField(default=100)
    price_per_person = MoneyField(help_text="Per head in kobo. ₦6,500.00 is 650000.")

    features = models.JSONField(default=list, blank=True)
    is_popular = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="catering/", null=True, blank=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "slug"], name="unique_catering_package_per_branch"
            ),
            models.CheckConstraint(
                condition=models.Q(max_guests__gte=models.F("min_guests")),
                name="catering_max_guests_gte_min",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def indicative_total(self, guest_count: int) -> int:
        """Guests × per-head price, in kobo.

        Indicative only. A real quote depends on the venue, the date and what
        the customer actually wants, which is why a human has to follow up.
        """
        return self.price_per_person * max(guest_count, 0)

    def suits(self, guest_count: int) -> bool:
        return self.min_guests <= guest_count <= self.max_guests


class CateringEnquiry(TimeStampedModel):
    """A request for a quote.

    Every field the existing form collects is captured, plus the things it
    cannot: a reference, a status, an owner and an SLA clock.
    """

    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="catering_enquiries")
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catering_enquiries",
    )

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = PhoneField()

    event_type = models.CharField(max_length=120, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    venue = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)

    package = models.ForeignKey(
        CateringPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enquiries",
    )
    indicative_total = MoneyField(
        help_text="Guests × per-head price at the time of enquiry. Indicative only."
    )

    status = models.CharField(
        max_length=20, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW, db_index=True
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_catering_enquiries",
    )
    internal_notes = models.TextField(blank=True, help_text="Never shown to the customer.")
    quoted_amount = MoneyField(null=True, blank=True, help_text="The real quote, in kobo.")
    responded_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "catering enquiries"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.reference} — {self.name} ({self.guest_count} guests)"

    @property
    def respond_by(self) -> dt.datetime:
        return self.created_at + RESPONSE_SLA

    @property
    def is_overdue(self) -> bool:
        """Past the 24 hours the website promises, and still unanswered."""
        if self.responded_at is not None or self.status not in AWAITING_RESPONSE:
            return False
        return timezone.now() > self.respond_by

    @property
    def hours_remaining(self) -> float:
        """Negative once the SLA has been breached."""
        return (self.respond_by - timezone.now()).total_seconds() / 3600
