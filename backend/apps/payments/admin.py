"""Payments admin — a ledger, not a workspace."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.common.admin import money_column
from apps.payments.models import PaymentTransaction, Refund, SavedPaymentMethod, WebhookEvent


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "our_reference",
        "order",
        "provider",
        "status",
        "amount_display",
        "card_summary",
        "verified_at",
    )
    list_filter = ("provider", "status", "channel")
    search_fields = ("our_reference", "provider_reference", "order__reference")
    date_hierarchy = "created_at"
    readonly_fields = tuple(field.name for field in PaymentTransaction._meta.fields)

    amount_display = money_column("amount", "Amount")

    @admin.display(description="Card")
    def card_summary(self, obj: PaymentTransaction) -> str:
        """Display only. There is no PAN here to show."""
        if not obj.card_last4:
            return "—"
        return f"{obj.card_brand or 'card'} ••••{obj.card_last4}"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "event_type",
        "event_id",
        "signature_valid",
        "processed_at",
        "created_at",
    )
    list_filter = ("provider", "signature_valid", "event_type")
    search_fields = ("event_id", "processing_error")
    date_hierarchy = "created_at"
    readonly_fields = tuple(field.name for field in WebhookEvent._meta.fields)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("order", "amount_display", "status", "initiated_by", "created_at")
    list_filter = ("status",)
    search_fields = ("order__reference", "provider_reference")
    date_hierarchy = "created_at"
    readonly_fields = tuple(field.name for field in Refund._meta.fields)

    amount_display = money_column("amount", "Amount")

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Refunds go through the API so the ledger, promo reversal and order
        # status all move together.
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    """Provider tokens the customer chose to keep.

    There is no card number here to show, and nothing on this page can be
    edited — a token is either valid at the provider or it is not.
    """

    list_display = (
        "user",
        "label",
        "provider",
        "is_default",
        "is_active",
        "is_expired",
        "last_used_at",
    )
    list_filter = ("provider", "is_active", "is_default")
    search_fields = ("user__email", "card_last4")
    readonly_fields = tuple(field.name for field in SavedPaymentMethod._meta.fields)

    @admin.display(boolean=True, description="Expired")
    def is_expired(self, obj: SavedPaymentMethod) -> bool:
        return obj.is_expired

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
