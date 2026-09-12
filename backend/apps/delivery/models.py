"""Delivery zones.

Phase 1B needs zones so an address can be resolved to a fee and an ETA.
``RiderProfile`` and ``DeliveryAssignment`` arrive in Phase 1D with orders.
"""

from __future__ import annotations

from django.db import models

from apps.common.fields import MoneyField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch


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
            'e.g. ["Victoria Island", "VI", "Eko Atlantic"]. Case-insensitive.'
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
        return [str(area).strip().lower() for area in (self.areas or []) if str(area).strip()]


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
