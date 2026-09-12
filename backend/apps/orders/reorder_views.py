"""Reorder and receipt endpoints.

Split out of ``views.py``, which already carries the order lifecycle and the
whole Kitchen Display System.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.serializers import serialise_cart
from apps.carts.services import cart as cart_services
from apps.carts.services.pricing import price_cart
from apps.carts.views import CART_TOKEN_HEADER
from apps.core.selectors import get_current_branch
from apps.orders.models import Order
from apps.orders.services.receipt import render_receipt_pdf
from apps.orders.services.reorder import reorder


class ReorderSerializer(serializers.Serializer):
    """Input for a reorder.

    ``replace`` is opt-in, and the endpoint answers 409 without it when the
    basket is not empty: a reorder that quietly discarded what the customer had
    already chosen would be destroying their work to save them a tap.
    """

    replace = serializers.BooleanField(default=False)


class ReorderView(APIView):
    """Rebuild the basket from a past order, at today's prices."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Reorder a past order",
        request=ReorderSerializer,
        parameters=[
            OpenApiParameter(
                CART_TOKEN_HEADER,
                str,
                OpenApiParameter.HEADER,
                description="Anonymous cart token, if the caller has one.",
            )
        ],
        tags=["orders"],
    )
    def post(self, request: Request, reference: str) -> Response:
        # Signed-in only, and scoped to the caller's own orders: a guest has no
        # durable basket to rebuild into, and reorder-by-reference would
        # otherwise let anyone enumerate what someone else ate.
        order = get_object_or_404(
            Order.objects.prefetch_related("items__modifiers"),
            reference=reference,
            user=request.user,
        )

        payload = ReorderSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        cart = cart_services.resolve_cart(
            branch=get_current_branch(),
            user=request.user,
            session_token=request.headers.get(CART_TOKEN_HEADER, ""),
        )
        result = reorder(order=order, cart=cart, replace=payload.validated_data["replace"])
        cart.refresh_from_db()

        body: dict[str, Any] = {
            "cart": serialise_cart(cart, price_cart(cart)),
            "added": len(result.added),
            "replaced_lines": result.replaced_lines,
            "changes": result.changes,
            "unavailable": result.unavailable,
        }
        if result.added_nothing:
            body["message"] = "Nothing from that order is available right now."
        elif not result.is_complete:
            body["message"] = "Some items could not be added. Check your basket before paying."

        return Response(body, status=status.HTTP_200_OK)


class ReceiptView(APIView):
    """A PDF receipt for a paid order."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Download a receipt",
        responses={(200, "application/pdf"): bytes},
        tags=["orders"],
    )
    def get(self, request: Request, reference: str) -> HttpResponse:
        from apps.orders.views import _may_read

        order = get_object_or_404(
            Order.objects.prefetch_related("items__modifiers"), reference=reference
        )
        if not _may_read(request, order):
            # 404 rather than 403: existence itself is not disclosed.
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        pdf = render_receipt_pdf(order)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt-{order.reference}.pdf"'
        return response


__all__ = ["ReceiptView", "ReorderSerializer", "ReorderView"]
