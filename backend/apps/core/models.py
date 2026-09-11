"""Branch, opening hours and site-wide settings."""

from __future__ import annotations

import datetime as dt

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.common.fields import MoneyField, PhoneField
from apps.common.models import SingletonModel, SoftDeleteModel, TimeStampedModel


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class Service(models.TextChoices):
    ALL_DAY = "all_day", "All day"
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    DINNER = "dinner", "Dinner"


class Branch(TimeStampedModel, SoftDeleteModel):
    """A restaurant location.

    There is exactly one row today. It exists as a table so that menus, prices,
    hours, zones and orders can hang off a foreign key — adding a second outlet
    later becomes a data change rather than a migration across the orders table.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)

    phone = PhoneField(blank=True)
    whatsapp = PhoneField(blank=True)
    email = models.EmailField(blank=True)

    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    currency = models.CharField(max_length=3, default="NGN")

    prices_include_vat = models.BooleanField(
        default=True,
        help_text=(
            "When on, menu prices are what the customer pays and VAT is extracted "
            "from them for accounting. When off, VAT is added at checkout. "
            "The published terms currently promise tax-inclusive pricing — see "
            "docs/PRD.md §7 before changing this."
        ),
    )
    vat_rate_bps = models.PositiveIntegerField(
        default=750,
        validators=[MaxValueValidator(10_000)],
        help_text="Basis points. 750 = 7.5%. Integer, so the rate can never drift.",
    )
    service_charge_bps = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(10_000)],
        help_text="Basis points applied to the order subtotal. 0 = none.",
    )

    is_accepting_orders = models.BooleanField(
        default=True,
        help_text="Manual kill switch. Turn off to stop new orders during a rush.",
    )
    min_order_value = MoneyField(help_text="Minimum order subtotal in kobo.")
    free_delivery_threshold = MoneyField(
        null=True,
        blank=True,
        help_text="Subtotal in kobo at which delivery becomes free. Blank = never.",
    )
    default_prep_minutes = models.PositiveSmallIntegerField(
        default=25,
        help_text="Fallback preparation time when a menu item has none.",
    )

    class Meta:
        verbose_name_plural = "branches"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    # ── Opening hours ─────────────────────────────────────────────────────────

    def local_now(self) -> dt.datetime:
        return timezone.localtime(timezone.now(), timezone=self.tzinfo())

    def tzinfo(self) -> dt.tzinfo:
        try:
            from zoneinfo import ZoneInfo

            return ZoneInfo(self.timezone)
        except Exception:
            return dt.UTC

    def is_open_at(self, moment: dt.datetime | None = None) -> bool:
        """Whether the branch is open at a given local moment.

        Holiday overrides win over the weekly schedule.
        """
        moment = moment or self.local_now()
        override = self.holiday_overrides.filter(date=moment.date()).first()
        if override is not None:
            if override.is_closed:
                return False
            if override.opens_at and override.closes_at:
                return override.opens_at <= moment.time() <= override.closes_at
            return True

        windows = self.opening_hours.filter(weekday=moment.weekday(), is_closed=False)
        return any(window.opens_at <= moment.time() <= window.closes_at for window in windows)

    @property
    def is_open_now(self) -> bool:
        return self.is_open_at()

    @property
    def can_accept_orders(self) -> bool:
        """Both switches must agree: published hours AND the manual override."""
        return self.is_active and self.is_accepting_orders and self.is_open_now


class OpeningHours(models.Model):
    """One opening window. Multiple rows per day support split services."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="opening_hours")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    service = models.CharField(max_length=20, choices=Service.choices, default=Service.ALL_DAY)
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    is_closed = models.BooleanField(default=False, help_text="Closed all day for this service.")

    class Meta:
        verbose_name_plural = "opening hours"
        ordering = ["weekday", "opens_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "weekday", "service"],
                name="unique_branch_weekday_service",
            ),
            models.CheckConstraint(
                condition=models.Q(closes_at__gt=models.F("opens_at")),
                name="closes_after_opens",
            ),
        ]

    def __str__(self) -> str:
        if self.is_closed:
            return f"{self.get_weekday_display()}: closed"
        return f"{self.get_weekday_display()}: {self.opens_at:%H:%M}–{self.closes_at:%H:%M}"


class HolidayOverride(models.Model):
    """A one-off change to the schedule. Wins over :class:`OpeningHours`."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="holiday_overrides")
    date = models.DateField(db_index=True)
    is_closed = models.BooleanField(default=True)
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "date"], name="unique_branch_holiday"),
        ]

    def __str__(self) -> str:
        return f"{self.date}: {'closed' if self.is_closed else 'special hours'}"


class SiteSettings(SingletonModel):
    """Site-wide content currently hardcoded in the frontend."""

    site_name = models.CharField(max_length=120, default="Kuyash Place Restaurant")
    tagline = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)

    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    support_email = models.EmailField(blank=True)
    orders_email = models.EmailField(blank=True)

    # Homepage statistics — hardcoded in the frontend hero today.
    stat_customers = models.CharField(max_length=20, blank=True)
    stat_dishes = models.CharField(max_length=20, blank=True)
    stat_years = models.CharField(max_length=20, blank=True)
    stat_rating = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self) -> str:
        return self.site_name
