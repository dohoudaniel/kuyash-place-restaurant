"""Dish reviews.

Replaces ``ReviewModal.tsx``, which showed "It will be published after
moderation", logged the review to the console, and was mounted nowhere — while
every dish displayed a hardcoded five stars.

A review belongs to one purchased order line (REV-5), so every review here is a
verified purchase (REV-1). Nothing is public until a manager approves it
(REV-3), and only approved reviews count towards a dish's rating (REV-4).
"""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Awaiting moderation"
    APPROVED = "approved", "Published"
    REJECTED = "rejected", "Not published"


class Review(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    menu_item = models.ForeignKey(
        "catalog.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews"
    )
    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=100)
    comment = models.TextField(max_length=1000)
    recommends = models.BooleanField(default=True)
    is_verified_purchase = models.BooleanField(default=False)

    status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING, db_index=True
    )
    moderated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_reviews",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(
        blank=True, help_text="Shown to the customer. Required when rejecting."
    )
    helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5"
            ),
            models.UniqueConstraint(
                fields=["user", "order_item"], name="one_review_per_order_line"
            ),
        ]
        indexes = [models.Index(fields=["menu_item", "status", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.rating}★ {self.title}"


class ReviewHelpfulVote(models.Model):
    """One "helpful" per voter per review, so the count cannot be pumped.

    ``voter_key`` is ``user:<id>`` for signed-in voters and a salted hash of the
    client address for anonymous ones — the address itself is never stored.
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    voter_key = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "voter_key"], name="one_helpful_vote_per_voter"
            )
        ]

    def __str__(self) -> str:
        return f"{self.voter_key} → {self.review_id}"
