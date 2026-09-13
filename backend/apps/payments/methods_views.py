"""Saved payment methods.

Every field exposed here is a provider token or a display fragment. There is
no endpoint in this module — or anywhere else — that accepts or returns a card
number.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import current_user
from apps.payments.models import SavedPaymentMethod


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    # Exposed as `card_label`, not `label`: DRF's Field uses `label` for the
    # human-readable field name, so declaring one here shadows it.
    card_label = serializers.CharField(source="label", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = SavedPaymentMethod
        fields = [
            "id",
            "provider",
            "card_label",
            "card_brand",
            "card_last4",
            "card_exp_month",
            "card_exp_year",
            "is_default",
            "is_expired",
            "last_used_at",
            "created_at",
        ]
        read_only_fields = fields


class PaymentMethodListView(APIView):
    """Cards the customer chose to keep."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="My saved payment methods",
        responses={200: SavedPaymentMethodSerializer(many=True)},
        tags=["payments"],
    )
    def get(self, request: Request) -> Response:
        methods = SavedPaymentMethod.objects.filter(user=current_user(request), is_active=True)
        return Response(SavedPaymentMethodSerializer(methods, many=True).data)


class PaymentMethodDetailView(APIView):
    """Forget a saved card."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Forget a saved card",
        responses={200: SavedPaymentMethodSerializer(many=True)},
        tags=["payments"],
    )
    def delete(self, request: Request, pk: str) -> Response:
        user = current_user(request)
        method = get_object_or_404(SavedPaymentMethod, pk=pk, user=user, is_active=True)

        # Deactivated rather than deleted: the token may still appear on a
        # historical transaction, and a hard delete would orphan that trail.
        method.is_active = False
        method.is_default = False
        method.save(update_fields=["is_active", "is_default", "updated_at"])

        remaining = SavedPaymentMethod.objects.filter(user=user, is_active=True)
        if not remaining.filter(is_default=True).exists() and (promoted := remaining.first()):
            promoted.is_default = True
            promoted.save(update_fields=["is_default", "updated_at"])

        return Response(
            SavedPaymentMethodSerializer(
                SavedPaymentMethod.objects.filter(user=user, is_active=True), many=True
            ).data
        )


class PaymentMethodDefaultView(APIView):
    """Choose which saved card is offered first."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Set the default payment method",
        request=None,
        responses={200: SavedPaymentMethodSerializer},
        tags=["payments"],
    )
    def post(self, request: Request, pk: str) -> Response:
        user = current_user(request)
        method = get_object_or_404(SavedPaymentMethod, pk=pk, user=user, is_active=True)

        SavedPaymentMethod.objects.filter(user=user, is_default=True).exclude(pk=method.pk).update(
            is_default=False
        )
        method.is_default = True
        method.save(update_fields=["is_default", "updated_at"])
        return Response(SavedPaymentMethodSerializer(method).data)


__all__: list[Any] = [
    "PaymentMethodDefaultView",
    "PaymentMethodDetailView",
    "PaymentMethodListView",
    "SavedPaymentMethodSerializer",
]
