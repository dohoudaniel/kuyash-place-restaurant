"""Academy admin — where staff publish courses, schedule classes and run enrolments."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.academy import services
from apps.academy.models import Cohort, Course, Enrolment, Instructor
from apps.common.admin import money_column
from apps.common.exceptions import DomainError
from apps.core.selectors import get_current_branch


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "bio")


class CohortInline(admin.TabularInline):
    model = Cohort
    extra = 0
    fields = (
        "starts_on",
        "ends_on",
        "capacity",
        "schedule_note",
        "status",
        "enrolled_count",
        "seats",
    )
    readonly_fields = ("enrolled_count", "seats")

    @admin.display(description="Seats left")
    def seats(self, obj: Cohort) -> int | str:
        return "—" if obj._state.adding else services.seats_left(obj)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "level",
        "course_type",
        "instructor",
        "price_display",
        "display_order",
        "is_active",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active", "level", "course_type", "instructor")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CohortInline]

    price_display = money_column("price", "Price")

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("branch", str(get_current_branch().pk))
        return initial


def _each(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Enrolment],
    action: Any,
    verb: str,
) -> None:
    done = 0
    for enrolment in queryset:
        try:
            action(enrolment)
            done += 1
        except DomainError as exc:
            modeladmin.message_user(request, f"{enrolment.reference}: {exc.detail}", messages.ERROR)
    if done:
        modeladmin.message_user(request, f"{verb} {done} enrolment(s).", messages.SUCCESS)


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "name",
        "course",
        "cohort",
        "status",
        "payment_method",
        "amount_display",
        "paid_at",
        "certificate_issued_at",
    )
    list_filter = ("status", "payment_method", "course", "cohort")
    search_fields = ("reference", "name", "email", "phone")
    date_hierarchy = "created_at"
    readonly_fields = tuple(
        field.name for field in Enrolment._meta.fields if field.name != "cancellation_reason"
    )
    actions = ["record_transfer", "complete_and_certify", "cancel"]

    amount_display = money_column("amount", "Fee")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.action(description="Record bank transfer received (confirms the seat)")
    def record_transfer(self, request: HttpRequest, queryset: QuerySet[Enrolment]) -> None:
        _each(
            self,
            request,
            queryset,
            lambda e: services.record_transfer(enrolment=e, actor=request.user),
            "Confirmed",
        )

    @admin.action(description="Mark completed and issue certificate")
    def complete_and_certify(self, request: HttpRequest, queryset: QuerySet[Enrolment]) -> None:
        _each(
            self, request, queryset, lambda e: services.complete_enrolment(enrolment=e), "Completed"
        )

    @admin.action(description="Cancel (refund any fee offline)")
    def cancel(self, request: HttpRequest, queryset: QuerySet[Enrolment]) -> None:
        _each(
            self,
            request,
            queryset,
            lambda e: services.cancel_enrolment(enrolment=e, reason="Cancelled by staff"),
            "Cancelled",
        )
