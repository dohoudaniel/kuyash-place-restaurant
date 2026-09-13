"""Payment endpoints.

**No endpoint in this module accepts a card number, expiry or CVV.** Card data
is entered on the provider's hosted checkout. See docs/PAYMENTS.md §1.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.serializers import money
from apps.common.permissions import IsManager
from apps.orders.models import Order
from apps.orders.views import _may_read
from apps.payments.models import Provider
from apps.payments.serializers import (
    InitialiseResponseSerializer,
    InitialiseSerializer,
    RefundResponseSerializer,
    RefundSerializer,
    VerifyResponseSerializer,
    WebhookAckSerializer,
)
from apps.payments.services import payments as payment_services
from apps.payments.services.webhooks import handle_webhook

logger = logging.getLogger(__name__)


class InitialisePaymentView(APIView):
    """Start (or retry) a payment and return the provider's checkout URL."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Initialise a payment",
        request=InitialiseSerializer,
        responses={201: InitialiseResponseSerializer},
        tags=["payments"],
    )
    def post(self, request: Request) -> Response:
        serializer = InitialiseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(Order, reference=serializer.validated_data["order"])
        if not _may_read(request, order):
            return Response(status=status.HTTP_404_NOT_FOUND)

        record = payment_services.initialise_payment(
            order=order,
            provider_name=serializer.validated_data.get("provider", ""),
            save_method=serializer.validated_data.get("save_card", False),
        )
        return Response(
            {
                "reference": record.our_reference,
                "provider": record.provider,
                "authorization_url": record.authorization_url,
                "amount": money(record.amount, record.currency),
                "order": order.reference,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):
    """Re-verify a payment.

    Called when the browser returns from the provider. The browser's return is
    a *hint to verify*, never proof: this endpoint asks the provider directly,
    so the outcome does not depend on anything the client asserts.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify a payment", responses={200: VerifyResponseSerializer}, tags=["payments"]
    )
    def get(self, request: Request, reference: str) -> Response:
        record = payment_services.verify_by_reference(reference)
        if record is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Re-read: settlement updates the order through its own query, so the
        # instance cached on the transaction still carries the old payment status.
        order = record.order
        order.refresh_from_db()
        return Response(
            {
                "status": record.status,
                "order_reference": order.reference,
                "order_status": order.status,
                "payment_status": order.payment_status,
                "amount": money(record.amount, record.currency),
            }
        )


class RefundView(APIView):
    """Refund an order. Managers only."""

    permission_classes = [IsManager]

    @extend_schema(
        summary="Refund an order",
        request=RefundSerializer,
        responses={200: RefundResponseSerializer},
        tags=["payments"],
    )
    def post(self, request: Request, reference: str) -> Response:
        serializer = RefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(Order, reference=reference)
        refund = payment_services.refund_order(
            order=order,
            amount_kobo=serializer.validated_data.get("amount"),
            reason=serializer.validated_data.get("reason", ""),
            actor=request.user,
        )
        order.refresh_from_db()
        return Response(
            {
                "order": order.reference,
                "amount": money(refund.amount, order.currency),
                "status": refund.status,
                "order_status": order.status,
                "payment_status": order.payment_status,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    """Provider webhooks.

    Unauthenticated by design (WH-5): the signature is the authentication.
    CSRF is exempt because the caller is a server, not a browser session.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    provider_name = ""

    @extend_schema(
        summary="Payment webhook",
        request=None,
        responses={200: WebhookAckSerializer},
        tags=["payments"],
    )
    def post(self, request: Request) -> Response:
        outcome = handle_webhook(
            provider_name=self.provider_name,
            raw_body=request.body,
            headers=request.headers,
            remote_addr=request.META.get("REMOTE_ADDR"),
        )
        if not outcome.accepted:
            return Response({"detail": outcome.detail}, status=status.HTTP_401_UNAUTHORIZED)
        # Always 200 on an accepted event, including ones we deliberately
        # ignore: a non-2xx makes the provider retry forever.
        return Response({"detail": outcome.detail}, status=status.HTTP_200_OK)


class PaystackWebhookView(WebhookView):
    provider_name = Provider.PAYSTACK


class FlutterwaveWebhookView(WebhookView):
    provider_name = Provider.FLUTTERWAVE
