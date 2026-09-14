"""Review endpoints."""

from __future__ import annotations

import hashlib
from typing import Any

from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.views import CsrfEnforcedMixin
from apps.common.client_ip import client_ip
from apps.common.pagination import PagePagination
from apps.common.permissions import IsManager, current_user
from apps.common.throttling import SCOPED_THROTTLES
from apps.core.selectors import get_current_branch
from apps.reviews import services
from apps.reviews.models import Review, ReviewStatus
from apps.reviews.serializers import (
    HelpfulResponseSerializer,
    ModerateSerializer,
    OwnReviewSerializer,
    ReviewCreateSerializer,
    ReviewInputSerializer,
    ReviewSerializer,
)

SORTS: dict[str, tuple[str, ...]] = {
    "newest": ("-created_at",),
    "helpful": ("-helpful_count", "-created_at"),
    "highest": ("-rating", "-created_at"),
    "lowest": ("rating", "-created_at"),
}


class ReviewListCreateView(ListAPIView):
    """Published reviews for a dish, and posting a new one."""

    serializer_class = ReviewSerializer
    pagination_class = PagePagination
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "review_create"

    def get_permissions(self) -> list[BasePermission]:
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self) -> Any:
        item = self.request.query_params.get("item", "").strip()
        if not item:
            raise serializers.ValidationError({"item": ["Choose a dish."]})
        ordering = SORTS.get(self.request.query_params.get("sort", ""), SORTS["newest"])
        return (
            Review.objects.filter(
                status=ReviewStatus.APPROVED,
                menu_item__slug=item,
                menu_item__branch=get_current_branch(),
            )
            .select_related("user")
            .order_by(*ordering)
        )

    @extend_schema(
        summary="List published reviews for a dish",
        parameters=[
            OpenApiParameter("item", OpenApiTypes.STR, required=True, description="Dish slug."),
            OpenApiParameter("sort", OpenApiTypes.STR, enum=list(SORTS), required=False),
        ],
        tags=["reviews"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Review a dish you received",
        request=ReviewCreateSerializer,
        responses={201: OwnReviewSerializer},
        tags=["reviews"],
    )
    def post(self, request: Request) -> Response:
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        review = services.create_review(
            user=current_user(request),
            order_line_id=data["order_line"],
            rating=data["rating"],
            title=data["title"],
            comment=data["comment"],
            recommends=data["recommends"],
        )
        return Response(OwnReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    """The author editing or removing their own review."""

    permission_classes = [IsAuthenticated]

    def _own(self, request: Request, review_id: Any) -> Review:
        return get_object_or_404(
            Review.objects.select_related("user", "menu_item", "order"),
            pk=review_id,
            user=current_user(request),
        )

    @extend_schema(
        summary="Retrieve your review", responses={200: OwnReviewSerializer}, tags=["reviews"]
    )
    def get(self, request: Request, review_id: Any) -> Response:
        return Response(OwnReviewSerializer(self._own(request, review_id)).data)

    @extend_schema(
        summary="Edit your review",
        description="Only within the edit window. The edited review returns to moderation.",
        request=ReviewInputSerializer(partial=True),
        responses={200: OwnReviewSerializer},
        tags=["reviews"],
    )
    def patch(self, request: Request, review_id: Any) -> Response:
        review = self._own(request, review_id)
        serializer = ReviewInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = {
            key: value for key, value in serializer.validated_data.items() if key in request.data
        }
        return Response(OwnReviewSerializer(services.update_review(review, **changes)).data)

    @extend_schema(summary="Delete your review", responses={204: None}, tags=["reviews"])
    def delete(self, request: Request, review_id: Any) -> Response:
        services.delete_review(self._own(request, review_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


def voter_key(request: Request) -> str:
    """Who is voting, without storing an address."""
    user = request.user
    if user and user.is_authenticated:
        return f"user:{user.pk}"
    address = client_ip(request)
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{address}".encode()).hexdigest()
    return f"anon:{digest[:64]}"


class ReviewHelpfulView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "review_vote"

    @extend_schema(
        summary="Mark a review as helpful",
        request=None,
        responses={200: HelpfulResponseSerializer},
        tags=["reviews"],
    )
    def post(self, request: Request, review_id: Any) -> Response:
        review = get_object_or_404(Review, pk=review_id)
        user = request.user if request.user.is_authenticated else None
        count, counted = services.mark_helpful(review, voter_key=voter_key(request), user=user)
        return Response({"helpful_count": count, "counted": counted})


class PendingReviewsView(ListAPIView):
    """The moderation queue, oldest first."""

    permission_classes = [IsManager]
    serializer_class = OwnReviewSerializer
    pagination_class = PagePagination

    def get_queryset(self) -> Any:
        return (
            Review.objects.filter(status=ReviewStatus.PENDING)
            .select_related("user", "menu_item", "order")
            .order_by("created_at")
        )

    @extend_schema(summary="Reviews awaiting moderation", tags=["reviews"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class ModerateReviewView(APIView):
    permission_classes = [IsManager]

    @extend_schema(
        summary="Approve or reject a review",
        request=ModerateSerializer,
        responses={200: OwnReviewSerializer},
        tags=["reviews"],
    )
    def post(self, request: Request, review_id: Any) -> Response:
        review = get_object_or_404(
            Review.objects.select_related("user", "menu_item", "order"), pk=review_id
        )
        serializer = ModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        review = services.moderate(
            review,
            moderator=current_user(request),
            approve=data["action"] == "approve",
            reason=data["reason"],
        )
        return Response(OwnReviewSerializer(review).data)
