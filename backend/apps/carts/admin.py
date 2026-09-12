"""Cart admin — read-only support view.

Carts are customer working state, not something staff should edit behind their
back. Read access answers "what did they actually have in the basket?".
"""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.carts.models import Cart, CartItem, CartItemModifier


class CartItemModifierInline(admin.TabularInline):
    model = CartItemModifier
    extra = 0


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = (
        "menu_item",
        "variant",
        "quantity",
        "unit_price_snapshot",
        "special_instructions",
    )
    show_change_link = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("__str__", "user", "status", "fulfilment_type", "promo_code", "updated_at")
    list_filter = ("status", "fulfilment_type", "branch")
    search_fields = ("user__email", "session_token")
    inlines = [CartItemInline]
    readonly_fields = tuple(field.name for field in Cart._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
