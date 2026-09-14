"""Loyalty admin. The ledger is append-only here too: corrections are new entries."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest

from apps.common.admin import money_column
from apps.core.selectors import get_current_branch
from apps.loyalty import services
from apps.loyalty.models import (
    LoyaltyAccount,
    LoyaltyTier,
    PointsLedgerEntry,
    Reward,
    RewardRedemption,
)


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = ("name", "min_points", "points_multiplier_bps", "birthday_points", "colour")


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "reward_type",
        "points_cost",
        "value_display",
        "stock",
        "display_order",
        "is_active",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active", "reward_type")
    search_fields = ("name", "description")
    autocomplete_fields = ("menu_item",)

    value_display = money_column("value", "Value")

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("branch", str(get_current_branch().pk))
        return initial


class LedgerInline(admin.TabularInline):
    model = PointsLedgerEntry
    fk_name = "account"
    extra = 0
    can_delete = False
    fields = ("created_at", "entry_type", "points", "description", "order", "created_by")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "points_balance", "lifetime_points", "tier", "is_closed")
    list_filter = ("tier", "is_closed")
    search_fields = ("user__email", "user__full_name")
    readonly_fields = (
        "user",
        "points_balance",
        "lifetime_points",
        "tier",
        "is_closed",
        "created_at",
    )
    fields = readonly_fields
    inlines = [LedgerInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


class AdjustmentForm(forms.ModelForm):
    class Meta:
        model = PointsLedgerEntry
        fields = ("account", "points", "description")
        help_texts = {
            "points": "Positive to add points, negative to remove them. A reason is required."
        }


@admin.register(PointsLedgerEntry)
class PointsLedgerEntryAdmin(admin.ModelAdmin):
    """Add an adjustment; nothing can be edited or deleted."""

    form = AdjustmentForm
    list_display = ("created_at", "account", "entry_type", "points", "description", "order")
    list_filter = ("entry_type",)
    search_fields = ("account__user__email", "description", "order__reference")
    date_hierarchy = "created_at"
    autocomplete_fields = ("account",)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def save_model(
        self, request: HttpRequest, obj: PointsLedgerEntry, form: Any, change: bool
    ) -> None:
        entry = services.adjust(
            account=obj.account, points=obj.points, description=obj.description, actor=request.user
        )
        obj.pk = entry.pk


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ("reward", "account", "order", "points_spent", "status", "created_at")
    list_filter = ("status", "reward")
    readonly_fields = tuple(field.name for field in RewardRedemption._meta.fields)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
