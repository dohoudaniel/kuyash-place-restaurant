"""Support serializers."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.support.models import (
    ChatMessage,
    ChatSender,
    ChatSession,
    ContactReason,
    FaqEntry,
    Ticket,
    TicketReply,
)


class ContactSerializer(serializers.Serializer):
    """Mirrors the fields the contact form already collects."""

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, default="", max_length=20)
    reason = serializers.ChoiceField(
        choices=ContactReason.values, required=False, default=ContactReason.GENERAL
    )
    subject = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)
    message = serializers.CharField(max_length=5000)
    # Hidden from humans by the form. Only a bot fills it in.
    website = serializers.CharField(required=False, allow_blank=True, default="")


class ContactAckSerializer(serializers.Serializer):
    reference = serializers.CharField(allow_blank=True)
    detail = serializers.CharField()

    class Meta:
        ref_name = "ContactAcknowledgement"


class TicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketReply
        fields = ["id", "body", "author_name", "created_at"]
        read_only_fields = fields

    def get_author_name(self, obj: TicketReply) -> str:
        return obj.author.get_short_name() if obj.author else "You"


class TicketSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "reference",
            "subject",
            "reason",
            "status",
            "status_display",
            "requester_name",
            "requester_email",
            "replies",
            "created_at",
        ]
        read_only_fields = fields

    def get_replies(self, obj: Ticket) -> list[dict]:
        """Internal notes are never exposed."""
        public = obj.replies.filter(is_internal_note=False)
        return list(TicketReplySerializer(public, many=True).data)


class CreateReplySerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000)


class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaqEntry
        fields = ["id", "question", "answer", "category", "helpful_count"]
        read_only_fields = fields


class OpenTicketsSerializer(serializers.Serializer):
    """Response envelope for ``GET /support/tickets/open/``."""

    count = serializers.IntegerField()
    tickets = TicketSerializer(many=True)


class ChatActionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[("order", "Order"), ("link", "Link")])
    url = serializers.CharField()

    class Meta:
        ref_name = "ChatAction"

    def get_fields(self) -> dict[str, serializers.Field]:
        # `label` would shadow DRF's own Field.label as a class attribute.
        fields = super().get_fields()
        fields["label"] = serializers.CharField()
        return fields


class ChatMessageSerializer(serializers.ModelSerializer):
    """One line of the conversation.

    ``suggestions``, ``can_escalate`` and ``action`` are set on assistant
    messages only.
    """

    sender = serializers.ChoiceField(choices=ChatSender.choices, read_only=True)
    suggestions = serializers.SerializerMethodField()
    can_escalate = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["sender", "body", "created_at", "suggestions", "can_escalate", "action"]
        read_only_fields = fields

    def get_suggestions(self, obj: ChatMessage) -> list[str]:
        return list((obj.extra or {}).get("suggestions") or [])

    def get_can_escalate(self, obj: ChatMessage) -> bool:
        return bool((obj.extra or {}).get("can_escalate"))

    @extend_schema_field(ChatActionSerializer(allow_null=True))
    def get_action(self, obj: ChatMessage) -> dict[str, str] | None:
        return (obj.extra or {}).get("action")


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    is_ended = serializers.SerializerMethodField()
    escalated_reference = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ["id", "messages", "is_ended", "escalated_reference", "created_at"]
        read_only_fields = fields

    def get_is_ended(self, obj: ChatSession) -> bool:
        return obj.ended_at is not None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_escalated_reference(self, obj: ChatSession) -> str | None:
        return obj.escalated_to_ticket.reference if obj.escalated_to_ticket else None


class ChatSessionCreatedSerializer(ChatSessionSerializer):
    token = serializers.CharField(
        source="session_token",
        read_only=True,
        help_text="Send as X-Chat-Token on every later request for this conversation.",
    )

    class Meta(ChatSessionSerializer.Meta):
        fields = [*ChatSessionSerializer.Meta.fields, "token"]
        read_only_fields = fields


class ChatSendSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=500, trim_whitespace=True)


class ChatExchangeSerializer(serializers.Serializer):
    message = ChatMessageSerializer()
    reply = ChatMessageSerializer()

    class Meta:
        ref_name = "ChatExchange"


class ChatEscalateSerializer(serializers.Serializer):
    """Name and email are taken from the account when signed in."""

    name = serializers.CharField(required=False, allow_blank=True, default="", max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    message = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class ChatEscalatedSerializer(serializers.Serializer):
    reference = serializers.CharField(allow_blank=True)
    reply = ChatMessageSerializer(allow_null=True)

    class Meta:
        ref_name = "ChatEscalated"
