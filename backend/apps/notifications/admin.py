"""Notification admin — read-only; this is a log, not a workspace."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.notifications.models import Notification


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
