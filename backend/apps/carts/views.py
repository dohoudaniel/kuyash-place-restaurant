"""Cart endpoints.

Guests carry an ``X-Cart-Token``; signed-in callers use their session. Every
response is the whole priced cart, so the client never has to reconcile a
partial update against its own arithmetic.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.models import Cart, CartItem, CartStatus
from apps.carts.serializers import (
    AddItemSerializer,
    CartResponseSerializer,
    FulfilmentSerializer,
    PromoSerializer,
    UpdateItemSerializer,
    serialise_cart,
)
from apps.carts.services import cart as cart_services
from apps.carts.services.pricing import price_cart
from apps.core.selectors import get_current_branch

CART_TOKEN_HEADER = "X-Cart-Token"  # noqa: S105 - a header name, not a credential


class CartBaseView(APIView):
    """Shared cart resolution and rendering."""

    permission_classes = [AllowAny]

    def get_cart(self, request: Request) -> Cart:
        return cart_services.resolve_cart(
            branch=get_current_branch(),
            user=request.user if request.user.is_authenticated else None,
            session_token=request.headers.get(CART_TOKEN_HEADER, ""),
        )

    def render(self, cart: Cart, *, status_code: int = status.HTTP_200_OK) -> Response:
        response = Response(serialise_cart(cart, price_cart(cart)), status=status_code)
        if cart.user_id is None:
            # Echo the token so an anonymous client can find this cart again.
            response[CART_TOKEN_HEADER] = cart.session_token
        return response


class CartView(CartBaseView):
    """The current cart, repriced on every read."""

    @extend_schema(
        summary="Get the current cart",
        responses={200: CartResponseSerializer},
        parameters=[
            OpenApiParameter(
                CART_TOKEN_HEADER,
                str,
                OpenApiParameter.HEADER,
                description="Anonymous cart identifier.",
            )
        ],
        tags=["cart"],
    )
    def get(self, request: Request) -> Response:
        return self.render(self.get_cart(request))

    @extend_schema(summary="Empty the cart", responses={200: CartResponseSerializer}, tags=["cart"])
    def delete(self, request: Request) -> Response:
        cart = self.get_cart(request)
        cart_services.clear(cart=cart)
        return self.render(cart)


class CartItemsView(CartBaseView):
    """Add a configured line."""

    @extend_schema(
        summary="Add an item to the cart",
        request=AddItemSerializer,
        responses={201: CartResponseSerializer},
        tags=["cart"],
    )
    def post(self, request: Request) -> Response:
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = self.get_cart(request)
        cart_services.add_item(
            cart=cart,
            item_slug=data["menu_item"],
            quantity=data["quantity"],
            variant_id=str(data["variant"]) if data.get("variant") else None,
            modifiers=data.get("modifiers") or [],
            special_instructions=data.get("special_instructions", ""),
        )
        return self.render(cart, status_code=status.HTTP_201_CREATED)


class CartItemDetailView(CartBaseView):
    """Change or remove one line."""

    def _get_item(self, request: Request, pk: str) -> tuple[Cart, CartItem]:
        cart = self.get_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        return cart, item

    @extend_schema(
        summary="Update a cart line",
        request=UpdateItemSerializer,
        responses={200: CartResponseSerializer},
        tags=["cart"],
    )
    def patch(self, request: Request, pk: str) -> Response:
        serializer = UpdateItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart, item = self._get_item(request, pk)
        cart_services.update_item(
            item=item,
            quantity=serializer.validated_data.get("quantity"),
            instructions=serializer.validated_data.get("special_instructions"),
        )
        return self.render(cart)

    @extend_schema(
        summary="Remove a cart line", responses={200: CartResponseSerializer}, tags=["cart"]
    )
    def delete(self, request: Request, pk: str) -> Response:
        cart, item = self._get_item(request, pk)
        item.delete()
        return self.render(cart)


class CartPromoView(CartBaseView):
    """Apply or remove a promo code."""

    throttle_scope = "promo_apply"

    @extend_schema(
        summary="Apply a promo code",
        request=PromoSerializer,
        responses={200: CartResponseSerializer},
        tags=["cart"],
    )
    def post(self, request: Request) -> Response:
        serializer = PromoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = self.get_cart(request)
        cart_services.apply_promo(cart=cart, code=serializer.validated_data["code"])
        return self.render(cart)

    @extend_schema(
        summary="Remove the promo code", responses={200: CartResponseSerializer}, tags=["cart"]
    )
    def delete(self, request: Request) -> Response:
        cart = self.get_cart(request)
        cart_services.remove_promo(cart=cart)
        return self.render(cart)


class CartFulfilmentView(CartBaseView):
    """Set delivery or pickup, the address and the tip."""

    @extend_schema(
        summary="Set fulfilment options",
        request=FulfilmentSerializer,
        responses={200: CartResponseSerializer},
        tags=["cart"],
    )
    def patch(self, request: Request) -> Response:
        serializer = FulfilmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = self.get_cart(request)
        cart_services.set_fulfilment(
            cart=cart,
            fulfilment_type=data.get("fulfilment_type"),
            address_id=str(data["delivery_address"]) if data.get("delivery_address") else None,
            tip=data.get("tip"),
        )
        return self.render(cart)


class CartMergeView(CartBaseView):
    """Fold an anonymous cart into the signed-in one after login."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Merge a guest cart",
        request=None,
        responses={200: CartResponseSerializer},
        parameters=[
            OpenApiParameter(
                CART_TOKEN_HEADER,
                str,
                OpenApiParameter.HEADER,
                description="Token of the guest cart to merge in.",
            )
        ],
        tags=["cart"],
    )
    def post(self, request: Request) -> Response:
        branch = get_current_branch()
        user_cart = cart_services.resolve_cart(branch=branch, user=request.user)

        token = request.headers.get(CART_TOKEN_HEADER, "")
        guest_cart = (
            Cart.objects.filter(
                session_token=token, branch=branch, status=CartStatus.ACTIVE, user__isnull=True
            ).first()
            if token
            else None
        )
        if guest_cart is not None:
            cart_services.merge_carts(guest_cart=guest_cart, user_cart=user_cart)
        return self.render(user_cart)


__all__: list[Any] = [
    "CartFulfilmentView",
    "CartItemDetailView",
    "CartItemsView",
    "CartMergeView",
    "CartPromoView",
    "CartView",
]
