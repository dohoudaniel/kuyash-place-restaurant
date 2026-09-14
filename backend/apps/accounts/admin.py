"""Admin for accounts."""

from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("email", "full_name", "phone", "is_email_verified", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "is_email_verified", "groups")
    search_fields = ("email", "full_name", "phone")
    ordering = ("-date_joined",)
    actions = ["reset_two_factor"]
    readonly_fields = ("id", "date_joined", "last_login", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal"), {"fields": ("full_name", "phone")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": _(
                    "Roles are groups: customers, kitchen, riders, managers. "
                    "Grant is_staff only to people who need the admin."
                ),
            },
        ),
        (_("Dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "phone", "password1", "password2"),
            },
        ),
    )


def _reset_two_factor(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[User]
) -> None:
    """For a staff member who lost their phone. Superusers only; they re-enrol at next sign-in."""
    from apps.accounts.staff_mfa import reset_for

    if not request.user.is_superuser:
        modeladmin.message_user(
            request, "Only a superuser can reset two-factor authentication.", messages.ERROR
        )
        return
    reset = sum(1 for user in queryset if reset_for(user))
    modeladmin.message_user(
        request, f"Two-factor authentication reset for {reset} account(s).", messages.SUCCESS
    )


_reset_two_factor.short_description = "Reset two-factor authentication (lost phone)"  # type: ignore[attr-defined]
UserAdmin.reset_two_factor = _reset_two_factor  # type: ignore[attr-defined]
