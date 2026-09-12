"""Order admin.

Orders are the business's books. Status changes go through the state machine
(and the KDS), never through free-text editing on a changelist.
"""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.common.admin import money_column
from apps.orders.models import Order, OrderItem, OrderItemModifier, OrderStatusEvent


class OrderItemModifierInline(admin.TabularInline):
    model = OrderItemModifier
    extra = 0
    readonly_fields = ("name_snapshot", "price_delta", "quantity")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "name_snapshot",
        "variant_name_snapshot",
        "quantity",
        "unit_price",
        "line_subtotal",
        "line_discount",
        "line_vat",
        "special_instructions",
    )
    can_delete = False
    show_change_link = True


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = (
        "from_status",
        "to_status",
        "actor",
        "actor_role",
        "source",
        "note",
        "created_at",
    )
    can_delete = False
    ordering = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "status",
        "payment_status",
        "fulfilment_type",
        "total_display",
        "placed_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "fulfilment_type", "branch")
    search_fields = ("reference", "guest_email", "user__email", "recipient_phone")
    date_hierarchy = "placed_at"
    inlines = [OrderItemInline, OrderStatusEventInline]

    # Every value here is a snapshot of what the customer agreed to. Editing one
    # would rewrite history rather than correct it; issue a refund instead.
    readonly_fields = tuple(field.name for field in Order._meta.fields)

    total_display = money_column("grand_total", "Total")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(OrderStatusEvent)
class OrderStatusEventAdmin(admin.ModelAdmin):
    """The audit trail. Append-only by construction."""

    list_display = ("order", "from_status", "to_status", "actor_role", "source", "created_at")
    list_filter = ("to_status", "source")
    search_fields = ("order__reference",)
    readonly_fields = tuple(field.name for field in OrderStatusEvent._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
