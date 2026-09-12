"""Notification admin — read-only; this is a log, not a workspace."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.notifications.models import EmailTemplate, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("template_key", "recipient", "status", "attempts", "sent_at", "created_at")
    list_filter = ("status", "channel", "template_key")
    search_fields = ("recipient", "subject", "template_key")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """Staff edit wording here; the code decides only when to send."""

    list_display = ("key", "subject", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "subject", "text_body")
    readonly_fields = ("id", "key", "available_context", "created_at", "updated_at")

    fieldsets = (
        (
            None,
            {
                "fields": ("key", "description", "is_active"),
                "description": (
                    "The <strong>key</strong> is referenced in code and cannot be changed. "
                    "Turning a template off falls back to the built-in wording — it does "
                    "not stop the email being sent."
                ),
            },
        ),
        (
            "Content",
            {
                "fields": ("subject", "text_body", "html_body", "available_context"),
                "description": (
                    "Use <code>{placeholder}</code> for values. The available placeholders "
                    "for this template are listed below. A placeholder that does not exist "
                    "makes the email fall back to the built-in wording rather than fail."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        # Deleting a row silently reverts to the built-in wording; deactivating
        # does the same thing visibly.
        return False
