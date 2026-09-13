"""Review serializers."""

from __future__ import annotations

import datetime as dt
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.reviews import services
from apps.reviews.models import Review, ReviewStatus


class ReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=100, trim_whitespace=True)
    comment = serializers.CharField(max_length=1000, trim_whitespace=True)
    recommends = serializers.BooleanField(required=False, default=True)


class ReviewCreateSerializer(ReviewInputSerializer):
    order_line = serializers.UUIDField(
        help_text="The `id` of a line on one of your delivered orders."
    )


class ReviewItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()

    class Meta:
        ref_name = "ReviewItem"


class ReviewSerializer(serializers.ModelSerializer):
    """A published review, as anyone sees it."""

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields: tuple[str, ...] = (
            "id",
            "rating",
            "title",
            "comment",
            "recommends",
            "author_name",
            "is_verified_purchase",
            "helpful_count",
            "created_at",
        )
        read_only_fields = fields

    def get_author_name(self, obj: Review) -> str:
        return services.author_name(obj)


class OwnReviewSerializer(ReviewSerializer):
    """A review as its author, or a moderator, sees it."""

    status = serializers.ChoiceField(choices=ReviewStatus.choices, read_only=True)
    menu_item = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    editable_until = serializers.SerializerMethodField()

    class Meta(ReviewSerializer.Meta):
        fields = (
            *ReviewSerializer.Meta.fields,
            "status",
            "rejection_reason",
            "menu_item",
            "order_reference",
            "can_edit",
            "editable_until",
        )
        read_only_fields = fields

    @extend_schema_field(ReviewItemSerializer(allow_null=True))
    def get_menu_item(self, obj: Review) -> dict[str, Any] | None:
        item = obj.menu_item
        return {"slug": item.slug, "name": item.name} if item else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_order_reference(self, obj: Review) -> str | None:
        return obj.order.reference if obj.order else None

    def get_can_edit(self, obj: Review) -> bool:
        return services.can_edit(obj)

    def get_editable_until(self, obj: Review) -> dt.datetime:
        return services.editable_until(obj)


class ModerateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
        help_text="Shown to the customer. Required when rejecting.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["action"] == "reject" and not attrs["reason"].strip():
            raise serializers.ValidationError(
                {"reason": ["Tell the customer why their review was not published."]}
            )
        return attrs


class HelpfulResponseSerializer(serializers.Serializer):
    helpful_count = serializers.IntegerField()
    counted = serializers.BooleanField(help_text="False when this voter had already voted.")

    class Meta:
        ref_name = "ReviewHelpful"
