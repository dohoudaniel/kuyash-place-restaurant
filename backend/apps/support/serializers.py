"""Support serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.support.models import ContactReason, FaqEntry, Ticket, TicketReply


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
