"""Menu catalogue.

Replaces ``frontend/lib/data/menu.ts`` and ``frontend/lib/assets/images.ts``.
Staff edit this in the admin; changing a price is no longer a code deploy.
"""

from __future__ import annotations

import datetime as dt

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.fields import MoneyField, SignedMoneyField
from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel
from apps.core.models import Branch, Weekday


class TaxClass(models.TextChoices):
    """Per-item VAT treatment.

    VAT is summed per line by tax class, never applied to the order subtotal —
    otherwise a zero-rated item is silently taxed through the total.
    """

    STANDARD = "standard", "Standard rated"
    ZERO_RATED = "zero_rated", "Zero rated"
    EXEMPT = "exempt", "Exempt"


class Category(TimeStampedModel, SoftDeleteModel):
    """A menu section, e.g. Burgers."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    emoji = models.CharField(max_length=8, blank=True, help_text="Shown beside the category name.")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "slug"], name="unique_category_slug_per_branch"
            )
        ]

    def __str__(self) -> str:
        return f"{self.emoji} {self.name}".strip()


class DietaryTag(models.Model):
    """A dietary attribute customers filter by.

    Makes the dietary filter real. The frontend currently carries a filter UI
    backed by the comment "Mock: would filter based on item dietary properties".
    """

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=8, blank=True)
    is_allergen = models.BooleanField(
        default=False,
        help_text="Allergen warnings are shown prominently rather than as a filter chip.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name


class MenuItemQuerySet(models.QuerySet["MenuItem"]):
    def orderable(self) -> MenuItemQuerySet:
        """Items a customer may actually put in a cart.

        ``needs_repricing`` is the gate that makes launching with placeholder
        prices structurally impossible rather than merely discouraged.
        """
        return self.filter(is_active=True, needs_repricing=False)

    def available_now(self, moment: dt.datetime | None = None) -> MenuItemQuerySet:
        """Orderable, not 86'd, and inside any configured time window."""
        moment = moment or timezone.now()
        local = timezone.localtime(moment)
        return (
            self.orderable()
            .filter(is_available_now=True)
            .exclude(
                models.Q(availability_windows__isnull=False)
                & ~models.Q(
                    availability_windows__weekday=local.weekday(),
                    availability_windows__starts_at__lte=local.time(),
                    availability_windows__ends_at__gte=local.time(),
                )
            )
            .distinct()
        )


class MenuItem(TimeStampedModel, SoftDeleteModel):
    """A dish.

    Identity is the ``slug`` — a stable, server-owned value. The frontend
    currently derives an item id from ``imageKey || slugify(name)``, so renaming
    a dish silently orphans every cart, wishlist and order-history row that
    referenced it.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="menu_items")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160)
    description = models.TextField(blank=True)

    base_price = MoneyField(help_text="Price in kobo. ₦1,250.00 is 125000.")
    compare_at_price = MoneyField(
        null=True,
        blank=True,
        help_text="Optional 'was' price for a strike-through. Leave blank for none.",
    )
    needs_repricing = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "ON means the price is an unconfirmed placeholder. Such items are "
            "hidden from the public API and block deployment. Turn OFF only once "
            "a real naira price has been set."
        ),
    )
    tax_class = models.CharField(max_length=20, choices=TaxClass.choices, default=TaxClass.STANDARD)

    prep_time_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Drives the order ETA. Blank falls back to the branch default.",
    )
    calories = models.PositiveIntegerField(null=True, blank=True)
    allergen_note = models.CharField(max_length=255, blank=True)
    dietary_tags = models.ManyToManyField(DietaryTag, blank=True, related_name="items")

    is_available_now = models.BooleanField(
        default=True,
        help_text="Turn off to '86' an item immediately without unpublishing it.",
    )
    is_featured = models.BooleanField(default=False, help_text="Surfaces in What's Hot.")
    display_order = models.PositiveIntegerField(default=0)

    # Denormalised, recalculated by background tasks. Never edited by hand.
    average_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    review_count = models.PositiveIntegerField(default=0)
    order_count = models.PositiveIntegerField(default=0)

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the item first went live. Powers 'sort by newest'.",
    )

    objects = MenuItemQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "slug"], name="unique_item_slug_per_branch")
        ]
        indexes = [
            models.Index(fields=["branch", "category", "is_active", "display_order"]),
            models.Index(fields=["branch", "is_featured"]),
            models.Index(fields=["branch", "needs_repricing"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        if self.is_active and self.published_at is None and not self.needs_repricing:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @property
    def is_orderable(self) -> bool:
        return self.is_active and not self.needs_repricing

    def available_at(self, moment: dt.datetime | None = None) -> bool:
        """Whether the item can be ordered at a given moment."""
        if not self.is_orderable or not self.is_available_now:
            return False
        windows = list(self.availability_windows.all())
        if not windows:
            return True
        local = timezone.localtime(moment or timezone.now())
        return any(
            window.weekday == local.weekday() and window.starts_at <= local.time() <= window.ends_at
            for window in windows
        )

    @property
    def effective_prep_minutes(self) -> int:
        return self.prep_time_minutes or self.branch.default_prep_minutes


class MenuItemImage(models.Model):
    """A photo. Uploaded by staff, served from Supabase Storage in production."""

    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="menu/")
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "display_order"]

    def __str__(self) -> str:
        return f"{self.item.name} image"


class AvailabilityWindow(models.Model):
    """A time window in which an item may be ordered.

    No windows means always available. This is what makes breakfast items
    actually breakfast-only instead of orderable at 21:00.
    """

    item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name="availability_windows"
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    class Meta:
        ordering = ["weekday", "starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="availability_ends_after_start",
            ),
            models.UniqueConstraint(
                fields=["item", "weekday", "starts_at"], name="unique_item_window"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} {self.starts_at:%H:%M}–{self.ends_at:%H:%M}"


class Variant(UUIDModel):
    """A size or portion choice. Exactly one is chosen per line."""

    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=80)
    price_delta = SignedMoneyField(
        help_text="Added to the base price, in kobo. May be negative for a smaller portion."
    )
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["item", "name"], name="unique_variant_per_item"),
            models.UniqueConstraint(
                fields=["item"],
                condition=models.Q(is_default=True),
                name="one_default_variant_per_item",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.item.name} — {self.name}"


class ModifierGroup(UUIDModel):
    """A set of options attached to one item.

    Per item, deliberately. The frontend currently renders a single global
    ``MOCK_CUSTOMIZATIONS`` array on every dish, so pancakes are offered extra
    cheese and none of the selections affect the price.
    """

    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="modifier_groups")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    min_select = models.PositiveSmallIntegerField(
        default=0, help_text="0 makes the group optional."
    )
    max_select = models.PositiveSmallIntegerField(
        default=1, help_text="1 is a radio, >1 checkboxes."
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_select__gte=models.F("min_select")),
                name="max_select_gte_min_select",
            ),
            models.CheckConstraint(
                condition=models.Q(max_select__gte=1), name="max_select_at_least_one"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.item.name} — {self.name}"

    @property
    def is_required(self) -> bool:
        return self.min_select > 0


class Modifier(UUIDModel):
    """One option within a group, with its own price effect."""

    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="modifiers")
    name = models.CharField(max_length=120)
    price_delta = SignedMoneyField(
        help_text="Added to the line price, in kobo. This is what makes an upgrade cost money."
    )
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["group", "name"], name="unique_modifier_per_group")
        ]

    def __str__(self) -> str:
        return self.name
