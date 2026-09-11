"""Core admin."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.common.admin import money_column
from apps.core.models import Branch, HolidayOverride, OpeningHours, SiteSettings


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 0
    ordering = ("weekday", "opens_at")


class HolidayOverrideInline(admin.TabularInline):
    model = HolidayOverride
    extra = 0


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    inlines = [OpeningHoursInline, HolidayOverrideInline]
    list_display = (
        "name",
        "city",
        "is_accepting_orders",
        "is_open_now",
        "vat_display",
        "min_order_display",
        "is_active",
    )
    readonly_fields = ("id", "created_at", "updated_at", "is_open_now")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "is_active")}),
        ("Contact", {"fields": ("phone", "whatsapp", "email")}),
        ("Location", {"fields": ("address_line", "city", "state", "latitude", "longitude")}),
        ("Locale", {"fields": ("timezone", "currency")}),
        (
            "Pricing and tax",
            {
                "fields": ("prices_include_vat", "vat_rate_bps", "service_charge_bps"),
                "description": (
                    "<strong>Read docs/PRD.md §7 before changing VAT direction.</strong> "
                    "The published terms and help pages promise tax-inclusive pricing."
                ),
            },
        ),
        (
            "Ordering",
            {
                "fields": (
                    "is_accepting_orders",
                    "min_order_value",
                    "free_delivery_threshold",
                    "default_prep_minutes",
                ),
                "description": "Money fields are in <strong>kobo</strong>: ₦1,500.00 is 150000.",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(boolean=True, description="Open now")
    def is_open_now(self, obj: Branch) -> bool:
        return obj.is_open_now

    @admin.display(description="VAT")
    def vat_display(self, obj: Branch) -> str:
        direction = "inclusive" if obj.prices_include_vat else "added at checkout"
        return f"{obj.vat_rate_bps / 100:g}% ({direction})"

    min_order_display = money_column("min_order_value", "Minimum order")
    free_delivery_display = money_column("free_delivery_threshold", "Free delivery over")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Singleton: one row, created on first access.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
