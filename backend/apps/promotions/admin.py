"""Promotions admin."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.common.admin import money_column
from apps.promotions.models import PromoCode, PromoRedemption


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "value_display",
        "min_order_display",
        "usage",
        "is_active",
        "valid_until",
    )
    list_filter = ("discount_type", "is_active", "is_public", "first_order_only", "branch")
    search_fields = ("code", "description")
    filter_horizontal = ("applicable_categories", "applicable_items")
    readonly_fields = ("id", "created_at", "updated_at", "usage")

    fieldsets = (
        (None, {"fields": ("id", "branch", "code", "description", "is_active")}),
        (
            "Discount",
            {
                "fields": ("discount_type", "value", "max_discount", "min_order_value"),
                "description": (
                    "<strong>Percentage</strong> discounts use basis points: 1000 = 10%.<br>"
                    "<strong>Fixed</strong> discounts and all money fields are in "
                    "<strong>kobo</strong>: ₦5,000.00 is 500000."
                ),
            },
        ),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        (
            "Limits",
            {
                "fields": ("usage_limit", "usage_limit_per_user", "first_order_only", "usage"),
                "description": "Counts come from the redemption ledger, not a stored counter.",
            },
        ),
        (
            "Targeting",
            {
                "fields": ("applicable_categories", "applicable_items"),
                "description": "Leave both empty to apply the code to the whole order.",
            },
        ),
        (
            "Visibility",
            {
                "fields": ("is_public",),
                "description": (
                    "Off by default. There is no endpoint that lists codes to customers."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    min_order_display = money_column("min_order_value", "Minimum order")

    @admin.display(description="Value")
    def value_display(self, obj: PromoCode) -> str:
        from apps.common.money import format_money

        if obj.discount_type == "percentage":
            return f"{obj.value / 100:g}%"
        if obj.discount_type == "fixed":
            return format_money(obj.value)
        return "free delivery"

    @admin.display(description="Used")
    def usage(self, obj: PromoCode) -> str:
        limit = obj.usage_limit if obj.usage_limit is not None else "∞"
        return f"{obj.times_used} / {limit}"


@admin.register(PromoRedemption)
class PromoRedemptionAdmin(admin.ModelAdmin):
    """Read-only: the ledger is a record, not a workspace."""

    list_display = (
        "promo_code",
        "user",
        "order_reference",
        "amount_display",
        "status",
        "created_at",
    )
    list_filter = ("status", "promo_code")
    search_fields = ("order_reference", "user__email", "promo_code__code")
    readonly_fields = tuple(field.name for field in PromoRedemption._meta.fields)
    date_hierarchy = "created_at"

    amount_display = money_column("discount_amount", "Discount")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
