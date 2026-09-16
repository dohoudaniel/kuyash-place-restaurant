"""Notification admin — read-only; this is a log, not a workspace."""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.notifications.models import EmailTemplate, Notification, NotificationStatus
from apps.notifications.services import dispatch


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("template_key", "recipient", "status", "attempts", "sent_at", "created_at")
    list_filter = ("status", "channel", "template_key")
    search_fields = ("recipient", "subject", "template_key")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)
    date_hierarchy = "created_at"
    actions = ["requeue"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    @admin.action(description="Requeue for delivery (a failed or stuck send)")
    def requeue(self, request: HttpRequest, queryset: QuerySet[Notification]) -> None:
        """The recovery path from a failed send.

        The rest of this page stays read-only — it is a log, not a workspace —
        but a log nobody can act on is no help at 7pm when a customer never
        received the verification email they need in order to sign in at all.

        Requeues stuck ``queued`` rows as well as ``failed`` ones: a task
        published before its transaction committed used to vanish, leaving the
        row queued forever with nothing to retry it.
        """
        if not request.user.has_perm("notifications.change_notification"):
            self.message_user(
                request,
                "You need change permission on notifications to requeue them.",
                messages.ERROR,
            )
            return

        requeued = 0
        for notification in queryset.exclude(status=NotificationStatus.SENT):
            notification.status = NotificationStatus.QUEUED
            notification.error = ""
            notification.save(update_fields=["status", "error", "updated_at"])
            dispatch(notification)
            requeued += 1

        already_sent = queryset.filter(status=NotificationStatus.SENT).count()
        self.message_user(request, f"Requeued {requeued} notification(s).", messages.SUCCESS)
        if already_sent:
            self.message_user(
                request,
                f"Skipped {already_sent} already sent — resending would deliver a duplicate.",
                messages.WARNING,
            )


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
