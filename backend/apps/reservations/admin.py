"""Reservations admin — the restaurant's book."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.common.admin import money_column
from apps.reservations.models import (
    BlackoutDate,
    Reservation,
    RestaurantTable,
    ServicePeriod,
    TableArea,
)


class RestaurantTableInline(admin.TabularInline):
    model = RestaurantTable
    extra = 0
    fields = ("number", "seats_min", "seats_max", "is_active")


@admin.register(TableArea)
class TableAreaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "table_count",
        "is_premium",
        "surcharge_display",
        "display_order",
        "is_active",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("branch", "is_premium", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [RestaurantTableInline]

    surcharge_display = money_column("surcharge", "Surcharge")

    @admin.display(description="Tables")
    def table_count(self, obj: TableArea) -> int:
        return obj.tables.filter(is_active=True).count()


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ("number", "area", "seats_min", "seats_max", "is_active")
    list_filter = ("area", "is_active", "branch")
    list_editable = ("seats_min", "seats_max", "is_active")
    search_fields = ("number",)


@admin.register(ServicePeriod)
class ServicePeriodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_weekday_display",
        "starts_at",
        "ends_at",
        "slot_interval_minutes",
        "turn_time_minutes",
        "is_active",
    )
    list_filter = ("weekday", "is_active", "branch")
    list_editable = ("slot_interval_minutes", "turn_time_minutes", "is_active")

    fieldsets = (
        (None, {"fields": ("branch", "name", "weekday", "is_active")}),
        (
            "Timing",
            {
                "fields": ("starts_at", "ends_at", "slot_interval_minutes", "turn_time_minutes"),
                "description": (
                    "<strong>Ends at</strong> is the last seating time, not closing time.<br>"
                    "<strong>Turn time</strong> is how long a table is held for one booking; "
                    "availability is calculated from it."
                ),
            },
        ),
    )


@admin.register(BlackoutDate)
class BlackoutDateAdmin(admin.ModelAdmin):
    list_display = ("date", "branch", "full_day", "starts_at", "ends_at", "reason")
    list_filter = ("branch", "full_day")
    date_hierarchy = "date"


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "reserved_for",
        "guest_name",
        "party_size",
        "area",
        "table",
        "status",
    )
    list_filter = ("status", "area", "source", "branch")
    search_fields = ("reference", "guest_name", "guest_email", "guest_phone")
    date_hierarchy = "reserved_for"
    readonly_fields = (
        "id",
        "reference",
        "confirmation_token",
        "idempotency_key",
        "created_at",
        "updated_at",
    )
    actions = ["mark_seated", "mark_completed", "mark_no_show"]

    fieldsets = (
        (None, {"fields": ("reference", "branch", "status", "source")}),
        (
            "Booking",
            {
                "fields": ("reserved_for", "duration_minutes", "party_size", "area", "table"),
                "description": (
                    "Changing the table here bypasses the availability check. "
                    "Use it to move a party at the door, not to take a booking."
                ),
            },
        ),
        (
            "Guest",
            {"fields": ("user", "guest_name", "guest_email", "guest_phone", "special_requests")},
        ),
        ("Cancellation", {"fields": ("cancellation_reason",), "classes": ("collapse",)}),
        (
            "Technical",
            {
                "fields": (
                    "id",
                    "confirmation_token",
                    "idempotency_key",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Mark as seated")
    def mark_seated(self, request: HttpRequest, queryset: QuerySet[Reservation]) -> None:
        from apps.reservations.models import ReservationStatus

        updated = queryset.update(status=ReservationStatus.SEATED)
        self.message_user(request, f"{updated} booking(s) marked seated.")

    @admin.action(description="Mark as completed")
    def mark_completed(self, request: HttpRequest, queryset: QuerySet[Reservation]) -> None:
        from apps.reservations.models import ReservationStatus

        updated = queryset.update(status=ReservationStatus.COMPLETED)
        self.message_user(request, f"{updated} booking(s) completed.")

    @admin.action(description="Mark as no-show")
    def mark_no_show(self, request: HttpRequest, queryset: QuerySet[Reservation]) -> None:
        from apps.reservations.models import ReservationStatus

        updated = queryset.update(status=ReservationStatus.NO_SHOW)
        self.message_user(request, f"{updated} booking(s) marked as no-show.")

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        """Surface today's covers on every visit."""
        from apps.reservations.models import OCCUPYING_STATUSES

        today = timezone.localdate()
        todays = Reservation.objects.filter(reserved_for__date=today, status__in=OCCUPYING_STATUSES)
        extra_context = extra_context or {}
        extra_context["todays_covers"] = sum(b.party_size for b in todays)
        return super().changelist_view(request, extra_context)
