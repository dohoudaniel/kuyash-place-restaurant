"""Support admin — the queue staff work from."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse

from apps.support.models import (
    ChatMessage,
    ChatSession,
    ContactMessage,
    FaqEntry,
    Ticket,
    TicketReply,
    TicketStatus,
)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """The raw submissions, including quarantined ones."""

    list_display = ("name", "email", "reason", "subject", "is_spam", "created_at")
    list_filter = ("reason", "is_spam", "branch")
    search_fields = ("name", "email", "subject", "message")
    date_hierarchy = "created_at"
    readonly_fields = tuple(field.name for field in ContactMessage._meta.fields)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 1
    fields = ("body", "is_internal_note", "author", "sent_email", "created_at")
    readonly_fields = ("sent_email", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "subject",
        "requester_name",
        "reason",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority", "reason", "assigned_to", "branch")
    search_fields = ("reference", "subject", "requester_name", "requester_email")
    date_hierarchy = "created_at"
    inlines = [TicketReplyInline]
    readonly_fields = ("id", "reference", "contact_message", "created_at", "updated_at")
    actions = ["mark_resolved"]
    ordering = ("status", "created_at")

    fieldsets = (
        (None, {"fields": ("reference", "branch", "subject", "reason")}),
        ("Requester", {"fields": ("user", "requester_name", "requester_email")}),
        (
            "Handling",
            {
                "fields": ("status", "priority", "assigned_to", "resolved_at"),
                "description": (
                    "Adding a reply below emails the customer unless it is marked as an "
                    "<strong>internal note</strong>. Internal notes are never shown to them."
                ),
            },
        ),
        (
            "Technical",
            {
                "fields": ("id", "contact_message", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Mark as resolved")
    def mark_resolved(self, request: HttpRequest, queryset: Any) -> None:
        from apps.support.services import resolve_ticket

        for ticket in queryset:
            resolve_ticket(ticket=ticket, actor=request.user)
        self.message_user(request, f"{queryset.count()} ticket(s) resolved.")

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        waiting = Ticket.objects.filter(status=TicketStatus.OPEN).count()
        if waiting:
            messages.warning(request, f"{waiting} ticket(s) have had no reply yet.")
        return super().changelist_view(request, extra_context)


@admin.register(FaqEntry)
class FaqEntryAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "display_order", "helpful_count", "is_active")
    list_editable = ("category", "display_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer")
    readonly_fields = ("helpful_count", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("question", "answer", "category", "display_order", "is_active")}),
        (
            "Matching",
            {
                "fields": ("keywords",),
                "description": (
                    "Extra terms that should match this answer. Used by the help page "
                    "search and, in Phase 3, the chat assistant — which can only ever "
                    "repeat what is written here."
                ),
            },
        ),
        (
            "Statistics",
            {"fields": ("helpful_count", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    can_delete = False
    fields = ("sender", "body", "matched_faq", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Read-only transcripts. Shows which questions the FAQ is failing to answer."""

    list_display = (
        "__str__",
        "user",
        "message_count",
        "escalated_to_ticket",
        "created_at",
        "ended_at",
    )
    list_filter = ("ended_at", "created_at")
    date_hierarchy = "created_at"
    inlines = [ChatMessageInline]
    fields = ("branch", "user", "escalated_to_ticket", "created_at", "updated_at", "ended_at")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(description="Messages")
    def message_count(self, obj: ChatSession) -> int:
        return obj.messages.count()
