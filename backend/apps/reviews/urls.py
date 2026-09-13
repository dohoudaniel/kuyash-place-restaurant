"""Review routes."""

from __future__ import annotations

from django.urls import path

from apps.reviews.views import (
    ModerateReviewView,
    PendingReviewsView,
    ReviewDetailView,
    ReviewHelpfulView,
    ReviewListCreateView,
)

app_name = "reviews"

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="list"),
    path("pending/", PendingReviewsView.as_view(), name="pending"),
    path("<uuid:review_id>/", ReviewDetailView.as_view(), name="detail"),
    path("<uuid:review_id>/helpful/", ReviewHelpfulView.as_view(), name="helpful"),
    path("<uuid:review_id>/moderate/", ModerateReviewView.as_view(), name="moderate"),
]
