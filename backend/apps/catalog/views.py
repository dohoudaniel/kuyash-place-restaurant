"""Catalogue endpoints. All public, all read-only."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import DietaryTag, MenuItem
from apps.catalog.selectors import base_queryset, categories_with_counts, filter_items
from apps.catalog.serializers import (
    CategorySerializer,
    DietaryTagSerializer,
    MenuItemDetailSerializer,
    MenuItemListSerializer,
)
from apps.common.pagination import PagePagination
from apps.core.selectors import get_current_branch


def _int_param(request: Request, name: str) -> int | None:
    """Parse a non-negative integer query parameter.

    Malformed input is ignored rather than fatal: a stray character in a URL
    should not turn the menu into a 400.
    """
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _decimal_param(request: Request, name: str) -> Decimal | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


class CategoryListView(ListAPIView):
    """Menu categories with orderable-item counts."""

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    @extend_schema(summary="List menu categories", tags=["catalog"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        return categories_with_counts(get_current_branch())


class DietaryTagListView(ListAPIView):
    """The dietary filter vocabulary."""

    permission_classes = [AllowAny]
    serializer_class = DietaryTagSerializer
    pagination_class = None
    queryset = DietaryTag.objects.all()

    @extend_schema(summary="List dietary tags", tags=["catalog"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class MenuItemListView(ListAPIView):
    """The menu, filtered and sorted server-side.

    Items with unconfirmed placeholder prices are excluded entirely.
    """

    permission_classes = [AllowAny]
    serializer_class = MenuItemListSerializer
    # Page, not cursor: cursor pagination imposes its own ordering and would
    # silently override the caller's `sort` parameter.
    pagination_class = PagePagination

    @extend_schema(
        summary="List menu items",
        tags=["catalog"],
        parameters=[
            OpenApiParameter("category", str, description="Category slug."),
            OpenApiParameter("search", str, description="Matches name and description."),
            OpenApiParameter(
                "dietary", str, description="Comma-separated tag slugs. AND semantics."
            ),
            OpenApiParameter("min_price", int, description="Minimum price in kobo."),
            OpenApiParameter("max_price", int, description="Maximum price in kobo."),
            OpenApiParameter("min_rating", str, description="Minimum average rating, 0–5."),
            OpenApiParameter("available_only", bool, description="Honour 86'd items and windows."),
            OpenApiParameter(
                "sort",
                str,
                description="popular | price_asc | price_desc | rating | newest",
            ),
        ],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        params = self.request.query_params
        dietary = [slug for slug in params.get("dietary", "").split(",") if slug]
        return filter_items(
            category=params.get("category", ""),
            search=params.get("search", ""),
            dietary=dietary,
            min_price=_int_param(self.request, "min_price"),
            max_price=_int_param(self.request, "max_price"),
            min_rating=_decimal_param(self.request, "min_rating"),
            available_only=params.get("available_only", "").lower() in {"1", "true", "yes"},
            sort=params.get("sort", "default"),
        )


class MenuItemDetailView(RetrieveAPIView):
    """One dish, with its variants and per-item modifier groups."""

    permission_classes = [AllowAny]
    serializer_class = MenuItemDetailSerializer
    lookup_field = "slug"

    @extend_schema(summary="Retrieve a menu item", tags=["catalog"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        return base_queryset()


class FeaturedItemsView(APIView):
    """What's Hot."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Featured items",
        responses={200: MenuItemListSerializer(many=True)},
        tags=["catalog"],
    )
    def get(self, request: Request) -> Response:
        items = filter_items(featured_only=True, sort="popular")[:12]
        return Response(MenuItemListSerializer(items, many=True).data, status=status.HTTP_200_OK)


__all__ = [
    "CategoryListView",
    "DietaryTagListView",
    "FeaturedItemsView",
    "MenuItem",
    "MenuItemDetailView",
    "MenuItemListView",
]
