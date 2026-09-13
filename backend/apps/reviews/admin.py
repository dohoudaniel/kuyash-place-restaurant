"""Reviews admin — the moderation queue managers work from."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest

from apps.reviews import services
from apps.reviews.models import Review, ReviewStatus


class ReviewAdminForm(ModelForm):
    class Meta:
        model = Review
        fields = ("status", "rejection_reason")

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        if (
            data.get("status") == ReviewStatus.REJECTED
            and not (data.get("rejection_reason") or "").strip()
        ):
            raise ValidationError(
                {"rejection_reason": "Tell the customer why it was not published."}
            )
        return data


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    form = ReviewAdminForm
    list_display = ("title", "rating", "menu_item", "user", "status", "helpful_count", "created_at")
    list_filter = ("status", "rating", "is_verified_purchase")
    search_fields = ("title", "comment", "user__email", "menu_item__name")
    date_hierarchy = "created_at"
    actions = ["approve_selected"]
    fields = (
        "menu_item",
        "user",
        "order",
        "rating",
        "title",
        "comment",
        "recommends",
        "is_verified_purchase",
        "helpful_count",
        "status",
        "rejection_reason",
        "moderated_by",
        "moderated_at",
        "created_at",
    )
    readonly_fields = tuple(name for name in fields if name not in {"status", "rejection_reason"})

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def save_model(self, request: HttpRequest, obj: Review, form: Any, change: bool) -> None:
        # Route every decision through the service so the dish's rating follows.
        if obj.status == ReviewStatus.PENDING:
            super().save_model(request, obj, form, change)
            services.recompute_item_rating(obj.menu_item_id)
            return
        services.moderate(
            obj,
            moderator=request.user,
            approve=obj.status == ReviewStatus.APPROVED,
            reason=obj.rejection_reason,
        )

    def delete_model(self, request: HttpRequest, obj: Review) -> None:
        services.delete_review(obj)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Review]) -> None:
        for review in queryset:
            services.delete_review(review)

    @admin.action(description="Approve and publish selected reviews")
    def approve_selected(self, request: HttpRequest, queryset: QuerySet[Review]) -> None:
        count = 0
        for review in queryset.exclude(status=ReviewStatus.APPROVED):
            services.moderate(review, moderator=request.user, approve=True)
            count += 1
        self.message_user(request, f"Published {count} review(s).", messages.SUCCESS)
