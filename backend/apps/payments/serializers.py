"""Payment serializers.

Every field here is deliberate. There is no ``card_number``, ``expiry`` or
``cvv`` — those are entered on the provider's hosted page.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import MoneySerializer
from apps.payments.models import Provider


class InitialiseSerializer(serializers.Serializer):
    order = serializers.CharField(max_length=20, help_text="Order reference, e.g. KYS-7Q2XF9.")
    provider = serializers.ChoiceField(
        choices=[Provider.PAYSTACK, Provider.FLUTTERWAVE],
        required=False,
        allow_blank=True,
        default="",
    )
    save_card = serializers.BooleanField(
        default=False,
        help_text=(
            "The customer's consent to keep this card for next time. Without it no "
            "provider token is stored, even though the provider returns one."
        ),
    )


class InitialiseSerializerMixin:
    """Marker for the shared docstring below."""


class RefundSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Amount in kobo. Omit to refund in full.",
    )
    reason = serializers.CharField(max_length=500, allow_blank=True, default="")


class InitialiseResponseSerializer(serializers.Serializer):
    """What the client needs to send the customer to hosted checkout."""

    reference = serializers.CharField()
    provider = serializers.CharField()
    authorization_url = serializers.URLField()
    amount = MoneySerializer()
    order = serializers.CharField()

    class Meta:
        ref_name = "PaymentInitialised"


class VerifyResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    order_reference = serializers.CharField()
    order_status = serializers.CharField()
    payment_status = serializers.CharField()
    amount = MoneySerializer()

    class Meta:
        ref_name = "PaymentVerification"


class RefundResponseSerializer(serializers.Serializer):
    order = serializers.CharField()
    amount = MoneySerializer()
    status = serializers.CharField()
    order_status = serializers.CharField()
    payment_status = serializers.CharField()

    class Meta:
        ref_name = "RefundResult"


class WebhookAckSerializer(serializers.Serializer):
    """Providers only need an acknowledgement."""

    detail = serializers.CharField()

    class Meta:
        ref_name = "WebhookAck"
