"""Wishlist endpoints.

Server-side so a saved dish survives a new device, a cleared browser and a
private window — none of which ``localStorage`` does.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import MenuItem, WishlistItem
from apps.catalog.serializers import MenuItemListSerializer
from apps.common.permissions import current_user


class AddToWishlistSerializer(serializers.Serializer):
    menu_item = serializers.SlugField()


class SyncWishlistSerializer(serializers.Serializer):
    """Folds a browser's saved list into the account on first sign-in."""

    menu_items = serializers.ListField(
        child=serializers.SlugField(), allow_empty=True, max_length=200
    )


class WishlistResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    items = MenuItemListSerializer(many=True)

    class Meta:
        ref_name = "Wishlist"


def _render(user: Any) -> dict[str, Any]:
    items = [
        entry.menu_item
        for entry in WishlistItem.objects.filter(user=user)
        .select_related("menu_item__category")
        .prefetch_related("menu_item__images", "menu_item__dietary_tags")
        if entry.menu_item.is_orderable
    ]
    return {"count": len(items), "items": MenuItemListSerializer(items, many=True).data}


class WishlistView(APIView):
    """The customer's saved dishes."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="My wishlist", responses={200: WishlistResponseSerializer}, tags=["wishlist"]
    )
    def get(self, request: Request) -> Response:
        return Response(_render(current_user(request)))

    @extend_schema(
        summary="Save a dish",
        request=AddToWishlistSerializer,
        responses={201: WishlistResponseSerializer},
        tags=["wishlist"],
    )
    def post(self, request: Request) -> Response:
        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = current_user(request)
        item = get_object_or_404(
            MenuItem.objects.orderable(), slug=serializer.validated_data["menu_item"]
        )
        # Saving twice is not an error — the customer wanted it saved, and it is.
        WishlistItem.objects.get_or_create(user=user, menu_item=item)
        return Response(_render(user), status=status.HTTP_201_CREATED)


class WishlistItemView(APIView):
    """Remove one saved dish."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove a saved dish",
        responses={200: WishlistResponseSerializer},
        tags=["wishlist"],
    )
    def delete(self, request: Request, slug: str) -> Response:
        user = current_user(request)
        WishlistItem.objects.filter(user=user, menu_item__slug=slug).delete()
        return Response(_render(user))


class WishlistSyncView(APIView):
    """Merge a browser's saved list into the account.

    Additive by design: signing in should never lose something the customer
    saved, on either side. Unknown or withdrawn slugs are reported rather than
    silently dropped, because the frontend's list is keyed on an image filename
    and will contain stale entries.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Merge a local wishlist",
        request=SyncWishlistSerializer,
        responses={200: WishlistResponseSerializer},
        tags=["wishlist"],
    )
    def post(self, request: Request) -> Response:
        serializer = SyncWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slugs = list(dict.fromkeys(serializer.validated_data["menu_items"]))

        user = current_user(request)
        found = {item.slug: item for item in MenuItem.objects.orderable().filter(slug__in=slugs)}
        for slug in slugs:
            if slug in found:
                WishlistItem.objects.get_or_create(user=user, menu_item=found[slug])

        payload = _render(user)
        payload["unmatched"] = [slug for slug in slugs if slug not in found]
        return Response(payload)
