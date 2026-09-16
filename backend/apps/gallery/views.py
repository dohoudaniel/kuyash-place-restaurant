"""Gallery endpoints."""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import TTL_MEDIUM, PublicCacheMixin
from apps.core.selectors import get_current_branch
from apps.gallery.models import GalleryCategory, GalleryImage
from apps.gallery.serializers import GalleryImageDetailSerializer, GalleryImageSerializer

FILTER_PARAMETERS = [
    OpenApiParameter("category", OpenApiTypes.STR, enum=GalleryCategory.values, required=False),
    OpenApiParameter("tag", OpenApiTypes.STR, required=False, description="Tag slug."),
    OpenApiParameter("featured", OpenApiTypes.BOOL, required=False),
]


def filtered_images(request: Request) -> QuerySet[GalleryImage]:
    """Published photos for the current branch, narrowed by the query string."""
    queryset = GalleryImage.objects.filter(branch=get_current_branch(), is_active=True)
    params = request.query_params

    category = params.get("category", "")
    if category:
        if category not in GalleryCategory.values:
            raise serializers.ValidationError(
                {"category": [f"Choose one of: {', '.join(GalleryCategory.values)}."]}
            )
        queryset = queryset.filter(category=category)
    tag = params.get("tag", "")
    if tag:
        queryset = queryset.filter(tags__slug=tag)
    if params.get("featured", "").lower() in {"1", "true"}:
        queryset = queryset.filter(is_featured=True)
    return queryset.distinct()


class GalleryListView(PublicCacheMixin, ListAPIView):
    """Every published photo, in display order.

    Not paginated: a restaurant gallery is tens of photos, and the page shows a
    count per category.
    """

    permission_classes = [AllowAny]
    serializer_class = GalleryImageSerializer
    pagination_class = None
    cache_max_age = TTL_MEDIUM

    def get_queryset(self) -> Any:
        return filtered_images(self.request).prefetch_related("tags")

    @extend_schema(summary="List gallery photos", parameters=FILTER_PARAMETERS, tags=["gallery"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class GalleryDetailView(PublicCacheMixin, APIView):
    permission_classes = [AllowAny]
    cache_max_age = TTL_MEDIUM

    @extend_schema(
        summary="Retrieve a photo with its neighbours",
        description="Neighbours follow the same filters as the list.",
        parameters=FILTER_PARAMETERS,
        responses={200: GalleryImageDetailSerializer},
        tags=["gallery"],
    )
    def get(self, request: Request, image_id: Any) -> Response:
        queryset = filtered_images(request)
        image = get_object_or_404(queryset.prefetch_related("tags"), pk=image_id)
        # Two `LIMIT 1` lookups rather than pulling every matching image id into
        # Python to find the two either side of this one. The keyset mirrors the
        # model's ordering, `(display_order ASC, created_at DESC)`, so "after"
        # means a higher display_order, or the same one and an older photo.
        image.previous_id = _neighbour(queryset, image, forwards=False)  # type: ignore[attr-defined]
        image.next_id = _neighbour(queryset, image, forwards=True)  # type: ignore[attr-defined]
        return Response(GalleryImageDetailSerializer(image).data)


def _neighbour(queryset: QuerySet[GalleryImage], image: GalleryImage, *, forwards: bool) -> Any:
    if forwards:
        after = Q(display_order__gt=image.display_order) | Q(
            display_order=image.display_order, created_at__lt=image.created_at
        )
        ordering = ("display_order", "-created_at")
    else:
        after = Q(display_order__lt=image.display_order) | Q(
            display_order=image.display_order, created_at__gt=image.created_at
        )
        ordering = ("-display_order", "created_at")
    return queryset.filter(after).order_by(*ordering).values_list("id", flat=True).first()
