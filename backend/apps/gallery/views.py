"""Gallery endpoints."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

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


class GalleryListView(ListAPIView):
    """Every published photo, in display order.

    Not paginated: a restaurant gallery is tens of photos, and the page shows a
    count per category.
    """

    permission_classes = [AllowAny]
    serializer_class = GalleryImageSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return filtered_images(self.request).prefetch_related("tags")

    @extend_schema(summary="List gallery photos", parameters=FILTER_PARAMETERS, tags=["gallery"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class GalleryDetailView(APIView):
    permission_classes = [AllowAny]

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
        ids = list(queryset.values_list("id", flat=True))
        index = ids.index(image.pk)
        image.previous_id = ids[index - 1] if index > 0 else None  # type: ignore[attr-defined]
        image.next_id = ids[index + 1] if index + 1 < len(ids) else None  # type: ignore[attr-defined]
        return Response(GalleryImageDetailSerializer(image).data)
