"""Catering admin — where enquiries actually reach a human."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from apps.catering.models import AWAITING_RESPONSE, CateringEnquiry, CateringPackage
from apps.common.admin import money_column


@admin.register(CateringPackage)
class CateringPackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "guest_range",
        "price_display",
        "is_popular",
        "display_order",
        "is_active",
    )
    list_editable = ("is_popular", "display_order", "is_active")
    list_filter = ("branch", "is_active", "is_popular")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "branch", "name", "slug", "description", "is_active")}),
        (
            "Pricing and size",
            {
                "fields": ("price_per_person", "min_guests", "max_guests"),
                "description": (
                    "<strong>Price per person is in kobo.</strong> ₦6,500.00 is 650000."
                ),
            },
        ),
        ("Presentation", {"fields": ("features", "image", "is_popular", "display_order")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    price_display = money_column("price_per_person", "Per head")

    @admin.display(description="Guests")
    def guest_range(self, obj: CateringPackage) -> str:
        return f"{obj.min_guests}–{obj.max_guests}"


@admin.register(CateringEnquiry)
class CateringEnquiryAdmin(admin.ModelAdmin):
    """The work queue. Ordered so the most urgent enquiry is at the top."""

    list_display = (
        "reference",
        "name",
        "guest_count",
        "event_date",
        "sla",
        "indicative_display",
        "status",
        "assigned_to",
    )
    list_filter = ("status", "branch", "package", "assigned_to")
    search_fields = ("reference", "name", "email", "phone", "venue")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "reference",
        "indicative_total",
        "ip_address",
        "respond_by",
        "created_at",
        "updated_at",
    )
    actions = ["mark_contacted", "mark_won", "mark_lost"]
    ordering = ("status", "created_at")

    fieldsets = (
        (None, {"fields": ("reference", "branch", "status", "assigned_to")}),
        ("Customer", {"fields": ("user", "name", "email", "phone")}),
        (
            "Event",
            {
                "fields": (
                    "event_type",
                    "event_date",
                    "event_time",
                    "guest_count",
                    "venue",
                    "message",
                ),
            },
        ),
        (
            "Quote",
            {
                "fields": ("package", "indicative_total", "quoted_amount", "responded_at"),
                "description": (
                    "<strong>Indicative total</strong> is guests × per-head price at the "
                    "time of enquiry — not a quote. Enter the real figure in "
                    "<strong>quoted amount</strong>, in kobo."
                ),
            },
        ),
        (
            "Internal",
            {"fields": ("internal_notes", "ip_address", "respond_by", "created_at", "updated_at")},
        ),
    )

    indicative_display = money_column("indicative_total", "Indicative")

    @admin.display(description="SLA")
    def sla(self, obj: CateringEnquiry) -> Any:
        if obj.responded_at is not None or obj.status not in AWAITING_RESPONSE:
            return format_html('<span style="color:{}">answered</span>', "#0a7d28")
        hours = obj.hours_remaining
        if hours < 0:
            return format_html(
                '<span style="color:{};font-weight:700">{} h overdue</span>',
                "#b00020",
                f"{-hours:.0f}",
            )
        return format_html('<span style="color:{}">{} h left</span>', "#8a6d00", f"{hours:.0f}")

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        """Say plainly how many customers are still waiting past the promise."""
        overdue = sum(
            1
            for enquiry in CateringEnquiry.objects.filter(status__in=AWAITING_RESPONSE)
            if enquiry.is_overdue
        )
        if overdue:
            messages.error(
                request,
                f"{overdue} catering enquiry(ies) are past the 24-hour response the "
                "website promises. Each one is a customer waiting on a quote.",
            )
        return super().changelist_view(request, extra_context)

    def _set_status(self, request: HttpRequest, queryset: Any, status: str, label: str) -> None:
        from apps.catering.services import record_response

        for enquiry in queryset:
            record_response(enquiry=enquiry, status=status, actor=request.user)
        self.message_user(
            request, f"{queryset.count()} enquiry(ies) marked {label}.", level=messages.SUCCESS
        )

    @admin.action(description="Mark as contacted (stops the SLA clock)")
    def mark_contacted(self, request: HttpRequest, queryset: Any) -> None:
        self._set_status(request, queryset, "contacted", "contacted")

    @admin.action(description="Mark as won")
    def mark_won(self, request: HttpRequest, queryset: Any) -> None:
        self._set_status(request, queryset, "won", "won")

    @admin.action(description="Mark as lost")
    def mark_lost(self, request: HttpRequest, queryset: Any) -> None:
        self._set_status(request, queryset, "lost", "lost")
