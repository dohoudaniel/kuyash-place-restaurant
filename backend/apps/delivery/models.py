"""Delivery zones.

Phase 1B needs zones so an address can be resolved to a fee and an ETA.
``RiderProfile`` and ``DeliveryAssignment`` arrive in Phase 1D with orders.
"""

from __future__ import annotations

import re
from typing import Any

from django.db import models

from apps.common.fields import MoneyField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch

#: Everything that is not a letter or a digit becomes a space, so
#: "Adeola Odeku, VI" and "adeola-odeku vi" normalise the same way.
_NOT_WORD = re.compile(r"[^0-9a-z]+")


def normalise_area(text: Any) -> str:
    """Fold an area name or an address line into comparable words."""
    return _NOT_WORD.sub(" ", str(text).lower()).strip()


class DeliveryZone(TimeStampedModel, SoftDeleteModel):
    """A named delivery area with a flat fee.

    Replaces the hardcoded ``₦5.00`` in the frontend's two cart components —
    a dollar figure that appeared in both by copy-paste.

    Phase 1 resolves a zone by matching area names. Phase 3 may add GeoJSON
    polygon containment; the ``polygon`` column is reserved for it.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="delivery_zones")
    name = models.CharField(max_length=120)
    slug = models.SlugField()

    fee = MoneyField(help_text="Flat delivery fee in kobo. ₦1,500.00 is 150000.")
    min_order_value = MoneyField(help_text="Minimum order subtotal for this zone, in kobo.")
    estimated_minutes = models.PositiveSmallIntegerField(
        default=40, help_text="Typical door-to-door time. Feeds the order ETA."
    )

    areas = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Area or district names matched against a customer's address, "
            'e.g. ["Victoria Island", "VI", "Eko Atlantic"]. Case-insensitive. '
            "Saving mirrors this list into the indexed DeliveryArea table that "
            "address matching actually queries."
        ),
    )
    polygon = models.TextField(
        blank=True,
        help_text="Reserved for GeoJSON boundary matching (Phase 3). Not used yet.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "slug"], name="unique_zone_slug_per_branch")
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def area_names(self) -> list[str]:
        return [name for name in (normalise_area(area) for area in (self.areas or [])) if name]

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        self.sync_areas()

    def sync_areas(self) -> None:
        """Mirror ``areas`` into the indexed table the matcher queries.

        Staff carry on editing the JSON list in the admin — that workflow is
        deliberately untouched — and this keeps :class:`DeliveryArea` in step
        with it. A queryset ``.update(areas=…)`` bypasses ``save()`` and so
        bypasses this; call ``sync_areas()`` yourself after one.
        """
        wanted: dict[str, str] = {}
        for raw in self.areas or []:
            name = str(raw).strip()
            normalised = normalise_area(name)
            if normalised:
                wanted.setdefault(normalised, name)

        existing = {row.normalised: row for row in self.area_rows.all()}
        stale = [row.pk for key, row in existing.items() if key not in wanted]
        if stale:
            DeliveryArea.objects.filter(pk__in=stale).delete()
        DeliveryArea.objects.bulk_create(
            [
                DeliveryArea(zone=self, name=name, normalised=key)
                for key, name in wanted.items()
                if key not in existing
            ]
        )


class DeliveryArea(models.Model):
    """One area name of one zone, normalised and indexed.

    ``DeliveryZone.areas`` — a JSON list — was substring-matched in Python on
    every address save and every checkout price: load every active zone, loop
    over every name, ask whether it appears anywhere in the address. Nothing
    about that can use an index, and it cost a scan per checkout.

    These rows are that list's indexed mirror. Matching is now by whole word
    rather than by raw substring, which is also more correct: "VI" no longer
    matches inside "Victoria Island" by accident.
    """

    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name="area_rows")
    name = models.CharField(max_length=120, help_text="As staff typed it.")
    normalised = models.CharField(
        max_length=120, help_text="Lower-cased, punctuation folded to spaces. Matched against."
    )

    class Meta:
        ordering = ["normalised"]
        constraints = [
            models.UniqueConstraint(fields=["zone", "normalised"], name="unique_area_per_zone")
        ]
        indexes = [models.Index(fields=["normalised"])]

    def __str__(self) -> str:
        return self.name


class VehicleType(models.TextChoices):
    BIKE = "bike", "Motorbike"
    CAR = "car", "Car"
    FOOT = "foot", "On foot"


class RiderProfile(TimeStampedModel):
    """A delivery rider."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="rider_profile"
    )
    vehicle_type = models.CharField(
        max_length=10, choices=VehicleType.choices, default=VehicleType.BIKE
    )
    is_on_shift = models.BooleanField(default=False)
    current_zone = models.ForeignKey(
        DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="riders"
    )

    def __str__(self) -> str:
        return self.user.get_full_name()


class DeliveryAssignment(TimeStampedModel):
    """Links one order to the rider carrying it.

    ``cash_collected`` is what a shift-end reconciliation compares against the
    sum of cash-on-delivery totals.
    """

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="delivery_assignment"
    )
    rider = models.ForeignKey(RiderProfile, on_delete=models.PROTECT, related_name="assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cash_collected = MoneyField(null=True, blank=True, help_text="For cash-on-delivery orders.")
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.order.reference} → {self.rider}"
