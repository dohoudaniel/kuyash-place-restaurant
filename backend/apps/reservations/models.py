"""Table reservations.

Replaces a three-step wizard that ends in ``alert("Reservation submitted!")``
and records nothing — so the restaurant has no idea the customer is coming.

The frontend has no concept of a table at all: it offers three *categories*
(indoor, outdoor, private), 18 always-available time slots, and party sizes up
to 20. Nothing can be double-booked there only because nothing can be booked.
"""

from __future__ import annotations

import datetime as dt
import secrets

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.fields import MoneyField, PhoneField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch, Weekday

RESERVATION_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_reference() -> str:
    """``RSV-XXXXXX`` — read aloud on the phone, so no 0/O or 1/I."""
    for _ in range(12):
        candidate = "RSV-" + "".join(secrets.choice(RESERVATION_ALPHABET) for _ in range(6))
        if not Reservation.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Could not allocate a reservation reference.")  # pragma: no cover


def generate_token() -> str:
    return secrets.token_urlsafe(32)


class ReservationStatus(models.TextChoices):
    PENDING = "pending", "Pending confirmation"
    CONFIRMED = "confirmed", "Confirmed"
    SEATED = "seated", "Seated"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No show"


#: Statuses that occupy a table. A cancelled booking frees the slot.
OCCUPYING_STATUSES = (
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.SEATED,
)


class ReservationSource(models.TextChoices):
    WEB = "web", "Website"
    PHONE = "phone", "Phone"
    WALK_IN = "walk_in", "Walk-in"


class TableArea(TimeStampedModel, SoftDeleteModel):
    """A seating area: indoor, outdoor patio, private room."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="table_areas")
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    features = models.JSONField(
        default=list, blank=True, help_text='e.g. ["Air conditioned", "Ambient music"]'
    )
    is_premium = models.BooleanField(default=False)
    surcharge = MoneyField(help_text="Per-booking surcharge in kobo. 0 for none.")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "slug"], name="unique_area_slug_per_branch")
        ]

    def __str__(self) -> str:
        return self.name


class RestaurantTable(TimeStampedModel, SoftDeleteModel):
    """A physical table.

    The thing the current UI has no concept of, and therefore the reason it can
    promise every slot to everyone.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="tables")
    area = models.ForeignKey(TableArea, on_delete=models.PROTECT, related_name="tables")
    number = models.CharField(max_length=10, help_text="As written on the table, e.g. 12 or P3.")
    seats_min = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Below this the table is wasted on the party.",
    )
    seats_max = models.PositiveSmallIntegerField(
        default=4, validators=[MinValueValidator(1), MaxValueValidator(50)]
    )

    class Meta:
        ordering = ["area__display_order", "number"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "number"], name="unique_table_number"),
            models.CheckConstraint(
                condition=models.Q(seats_max__gte=models.F("seats_min")),
                name="table_seats_max_gte_min",
            ),
        ]

    def __str__(self) -> str:
        return f"Table {self.number} ({self.seats_min}–{self.seats_max})"

    def fits(self, party_size: int) -> bool:
        return self.seats_min <= party_size <= self.seats_max


class ServicePeriod(models.Model):
    """A window during which tables may be booked.

    Availability is *computed* from these plus live bookings. The frontend
    hardcodes 18 slots from 11:00 to 22:00, always available.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="service_periods")
    name = models.CharField(max_length=60, help_text="Lunch, Dinner…")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    starts_at = models.TimeField()
    ends_at = models.TimeField(help_text="Last seating time, not closing time.")
    slot_interval_minutes = models.PositiveSmallIntegerField(
        default=30, validators=[MinValueValidator(5)]
    )
    turn_time_minutes = models.PositiveSmallIntegerField(
        default=90, help_text="How long a table is held for one booking."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "weekday", "name"], name="unique_service_period"
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="service_period_ends_after_start",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_weekday_display()} {self.name} {self.starts_at:%H:%M}–{self.ends_at:%H:%M}"
        )

    def slot_times(self) -> list[dt.time]:
        """Every bookable start time in this period."""
        times: list[dt.time] = []
        cursor = dt.datetime.combine(dt.date.today(), self.starts_at)
        limit = dt.datetime.combine(dt.date.today(), self.ends_at)
        step = dt.timedelta(minutes=self.slot_interval_minutes)
        while cursor <= limit:
            times.append(cursor.time())
            cursor += step
        return times


class BlackoutDate(models.Model):
    """A date the restaurant does not take bookings, or takes them differently."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="blackouts")
    date = models.DateField(db_index=True)
    reason = models.CharField(max_length=200, blank=True)
    full_day = models.BooleanField(default=True)
    starts_at = models.TimeField(null=True, blank=True)
    ends_at = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "date"], name="unique_blackout_per_date")
        ]

    def __str__(self) -> str:
        return f"{self.date}: {self.reason or 'closed'}"


class Reservation(TimeStampedModel):
    """A booked table."""

    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="reservations")
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    area = models.ForeignKey(
        TableArea,
        on_delete=models.PROTECT,
        related_name="reservations",
        help_text="What the customer asked for.",
    )
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservations",
        help_text="Allocated when the booking is made.",
    )

    reserved_for = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=90)
    party_size = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    guest_name = models.CharField(max_length=150)
    guest_email = models.EmailField()
    guest_phone = PhoneField()
    special_requests = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.CONFIRMED,
        db_index=True,
    )
    source = models.CharField(
        max_length=20, choices=ReservationSource.choices, default=ReservationSource.WEB
    )
    confirmation_token = models.CharField(
        max_length=64,
        default=generate_token,
        help_text="Lets a guest view or cancel this booking from the emailed link.",
    )
    cancellation_reason = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-reserved_for"]
        indexes = [
            models.Index(fields=["branch", "status", "reserved_for"]),
            models.Index(fields=["table", "reserved_for"]),
        ]
        constraints = [
            # The durable half of the idempotency guarantee. The cache is a
            # cache: it evicts, it can be flushed, and a Redis failover loses
            # the claim — at which point a retried submission books a second
            # table. This refuses that at the database, whatever the cache
            # believes. Partial, because staff and phone bookings legitimately
            # carry no key and several blanks are not a duplicate.
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_reservation_idempotency_key",
            )
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.guest_name} ×{self.party_size}"

    @property
    def ends_at(self) -> dt.datetime:
        return self.reserved_for + dt.timedelta(minutes=self.duration_minutes)

    @property
    def occupies_a_table(self) -> bool:
        return self.status in OCCUPYING_STATUSES

    @property
    def can_cancel(self) -> bool:
        return self.status in {ReservationStatus.PENDING, ReservationStatus.CONFIRMED}
