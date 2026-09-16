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

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="For bank transfer orders. Leave any bank field blank to switch transfer off.",
    )
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)

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

        The schedule is read through ``apps.core.selectors``, which caches it and
        drops that cache whenever a window or an override changes. So this costs
        no queries on the hot path — ``/core/branch/`` computed it three times
        per request — while still answering about *now* rather than about
        whenever the branch row happened to be cached.
        """
        from apps.core import selectors

        moment = moment or self.local_now()
        override = selectors.holiday_override_on(self, moment.date())
        if override is not None:
            if override.is_closed:
                return False
            if override.opens_at and override.closes_at:
                return override.opens_at <= moment.time() <= override.closes_at
            return True

        return any(
            window.opens_at <= moment.time() <= window.closes_at
            for window in selectors.opening_windows(self, moment.weekday())
        )

    @property
    def accepts_bank_transfer(self) -> bool:
        """Transfer is only offered once someone has entered where to send money.

        The checkout used to promise "You will receive bank transfer details after
        placing your order" when no such details existed anywhere in the system.
        """
        return bool(self.bank_name and self.bank_account_name and self.bank_account_number)

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

    established_year = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Shown on the About page. Leave blank to hide it."
    )

    # Headline figures. Each is shown only when filled in, so enter only what
    # the restaurant can stand behind.
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


class LegalPage(TimeStampedModel):
    """A published policy page.

    Replaces five hardcoded route files (`terms`, `privacy`, `cookies`,
    `refunds`, `accessibility`), and is where the tax-copy contradiction gets
    fixed: `app/terms/page.tsx:47` and `app/help/page.tsx:120` both promise
    tax-inclusive pricing while the cart adds 7.5% on top.

    **Versions are retained, not overwritten.** Which wording a customer agreed
    to matters if it is ever disputed, so a new version is a new row and the old
    one stays readable. ``(slug, version)`` is unique rather than ``slug``.
    """

    slug = models.SlugField(
        help_text="terms, privacy, cookies, refunds, accessibility…",
    )
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Markdown.")
    summary = models.CharField(
        max_length=300, blank=True, help_text="What changed in this version."
    )
    effective_from = models.DateField(
        default=dt.date.today, help_text="The date this wording takes effect."
    )
    published = models.BooleanField(
        default=False,
        help_text="Unpublished drafts are invisible to customers and to the API.",
    )

    class Meta:
        ordering = ["slug", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["slug", "version"], name="unique_legal_page_version")
        ]

    def __str__(self) -> str:
        return f"{self.title} v{self.version}"

    @classmethod
    def current(cls, slug: str, *, on: dt.date | None = None) -> LegalPage | None:
        """The wording in force on a given date.

        A version dated in the future is a scheduled change, not the current
        policy, so it is excluded until its date arrives.
        """
        on = on or timezone.localdate()
        return (
            cls.objects.filter(slug=slug, published=True, effective_from__lte=on)
            .order_by("-effective_from", "-version")
            .first()
        )

    @classmethod
    def next_version_for(cls, slug: str) -> int:
        highest = cls.objects.filter(slug=slug).order_by("-version").first()
        return (highest.version + 1) if highest else 1


def _image_validators() -> list:
    from django.core.validators import FileExtensionValidator

    from apps.gallery.models import IMAGE_EXTENSIONS, validate_image_size

    return [FileExtensionValidator(IMAGE_EXTENSIONS), validate_image_size]


class TeamMember(TimeStampedModel, SoftDeleteModel):
    """A person on the About page.

    Replaces four hardcoded profiles, including a founder "trained in Paris and
    Lagos" and an "award-winning" pastry chef, that nobody had confirmed.
    """

    name = models.CharField(max_length=150)
    role = models.CharField(max_length=120)
    bio = models.CharField(max_length=300, blank=True)
    photo = models.ImageField(
        upload_to="team/", null=True, blank=True, validators=_image_validators()
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.role}"


class Award(TimeStampedModel, SoftDeleteModel):
    """A recognition the restaurant has actually received.

    The About page used to credit the Michelin Guide, TripAdvisor and a "Lagos
    Food Awards" with honours nothing supports. None are seeded: an award is
    entered by someone who can point to it.
    """

    title = models.CharField(max_length=150)
    awarded_by = models.CharField(max_length=150)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    url = models.URLField(blank=True, help_text="Where the award can be verified.")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-year"]

    def __str__(self) -> str:
        return f"{self.title} — {self.awarded_by}"
