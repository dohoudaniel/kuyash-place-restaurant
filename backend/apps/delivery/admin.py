"""Delivery admin."""

from __future__ import annotations

from django.contrib import admin

from apps.common.admin import money_column
from apps.delivery.models import DeliveryAssignment, DeliveryZone, RiderProfile


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "fee_display",
        "min_order_display",
        "estimated_minutes",
        "is_active",
    )
    list_filter = ("branch", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "branch", "name", "slug", "display_order", "is_active")}),
        (
            "Pricing",
            {
                "fields": ("fee", "min_order_value", "estimated_minutes"),
                "description": (
                    "<strong>Fees are in kobo.</strong> ₦1,500.00 is entered as 150000.<br>"
                    "Seeded values are PLACEHOLDERS — set real ones before launch."
                ),
            },
        ),
        (
            "Matching",
            {
                "fields": ("areas", "polygon"),
                "description": (
                    "Addresses are matched against the area names listed here, "
                    "case-insensitively. Polygon matching is reserved for a later phase."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    fee_display = money_column("fee", "Fee")
    min_order_display = money_column("min_order_value", "Minimum order")


@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "vehicle_type", "is_on_shift", "current_zone")
    list_filter = ("vehicle_type", "is_on_shift", "current_zone")
    search_fields = ("user__email", "user__full_name")
    list_editable = ("is_on_shift",)


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ("order", "rider", "assigned_at", "delivered_at", "cash_display")
    list_filter = ("rider",)
    search_fields = ("order__reference", "rider__user__email")
    readonly_fields = ("order", "assigned_at")

    cash_display = money_column("cash_collected", "Cash collected")
