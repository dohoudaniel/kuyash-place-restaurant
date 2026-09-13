"""Order serializers."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.carts.serializers import money
from apps.common.serializers import MoneySerializer, TotalsSerializer
from apps.orders.models import Order, PaymentMethod
from apps.orders.services.state import timeline


class PlaceOrderSerializer(serializers.Serializer):
    """Input for placing an order.

    Contains no price field of any kind. ``expected_total`` is a *guard*, not an
    instruction: if it disagrees with the server's figure the order is refused
    rather than silently charged at a different amount.
    """

    payment_method = serializers.ChoiceField(choices=PaymentMethod.values)
    payment_provider = serializers.CharField(required=False, allow_blank=True, default="")
    customer_note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )
    expected_total = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="The grand total the customer was shown, in kobo.",
    )
    guest = serializers.DictField(required=False, default=dict)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=300)


class OrderListSerializer(serializers.ModelSerializer):
    """Compact shape for order history."""

    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = (
            "reference",
            "status",
            "status_display",
            "payment_status",
            "fulfilment_type",
            "placed_at",
            "total",
            "item_count",
        )
        read_only_fields = fields

    @extend_schema_field(MoneySerializer)
    def get_total(self, obj: Order) -> dict[str, Any]:
        return money(obj.grand_total, obj.currency)

    def get_item_count(self, obj: Order) -> int:
        return sum(line.quantity for line in obj.items.all())


def serialise_order(order: Order, *, include_token: bool = False) -> dict[str, Any]:
    """Full order detail — the polling payload."""
    currency = order.currency
    payload: dict[str, Any] = {
        "reference": order.reference,
        "status": order.status,
        "status_display": order.get_status_display(),
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "fulfilment_type": order.fulfilment_type,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "estimated_ready_at": (
            order.estimated_ready_at.isoformat() if order.estimated_ready_at else None
        ),
        "estimated_delivery_at": (
            order.estimated_delivery_at.isoformat() if order.estimated_delivery_at else None
        ),
        "timeline": timeline(order),
        "items": [
            {
                "name": line.name_snapshot,
                "slug": line.slug_snapshot,
                "variant_name": line.variant_name_snapshot,
                "quantity": line.quantity,
                "modifiers": [modifier.name_snapshot for modifier in line.modifiers.all()],
                "special_instructions": line.special_instructions,
                "unit_price": money(line.unit_price, currency),
                "line_subtotal": money(line.line_subtotal, currency),
                "image_url": line.image_url_snapshot or None,
            }
            for line in order.items.all()
        ],
        "delivery_address": (
            {
                "recipient_name": order.recipient_name,
                "phone": order.recipient_phone,
                "street": order.street,
                "area": order.area,
                "city": order.city,
                "state": order.state,
                "landmark": order.landmark,
                "delivery_notes": order.delivery_notes,
                "zone": order.delivery_zone_name,
            }
            if order.fulfilment_type == "delivery"
            else None
        ),
        "totals": {
            "subtotal": money(order.subtotal, currency),
            "discount": money(order.discount_total, currency),
            "delivery_fee": money(order.delivery_fee, currency),
            "service_charge": money(order.service_charge, currency),
            "vat": money(order.vat_total, currency),
            "tip": money(order.tip, currency),
            "grand_total": money(order.grand_total, currency),
        },
        "promo_code": order.promo_code_snapshot,
        "customer_note": order.customer_note,
        "can_cancel": order.can_cancel,
    }

    assignment = getattr(order, "delivery_assignment", None)
    payload["rider"] = (
        {"name": assignment.rider.user.get_short_name(), "phone": assignment.rider.user.phone}
        if assignment
        else None
    )
    if include_token:
        payload["guest_token"] = order.guest_token
    return payload


def kds_ticket(order: Order) -> dict[str, Any]:
    """The kitchen's view of an order.

    Modifiers and special instructions are first-class here: they are what the
    kitchen actually cooks from, and they are exactly what the current frontend
    collects and then discards.
    """
    from django.utils import timezone

    elapsed = int((timezone.now() - (order.placed_at or order.created_at)).total_seconds())
    is_late = bool(
        order.estimated_ready_at
        and timezone.now() > order.estimated_ready_at
        and order.status not in {"ready", "out_for_delivery", "delivered"}
    )
    return {
        "reference": order.reference,
        "status": order.status,
        "placed_at": (order.placed_at or order.created_at).isoformat(),
        "elapsed_seconds": elapsed,
        "is_late": is_late,
        "fulfilment_type": order.fulfilment_type,
        "zone": order.delivery_zone_name,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "requires_cash_collection": order.payment_method == "cash",
        "items": [
            {
                "quantity": line.quantity,
                "name": line.name_snapshot,
                "variant": line.variant_name_snapshot,
                "modifiers": [modifier.name_snapshot for modifier in line.modifiers.all()],
                "special_instructions": line.special_instructions,
            }
            for line in order.items.all()
        ],
        "customer_note": order.customer_note,
        "customer": {"name": order.contact_name, "phone": order.recipient_phone},
        "grand_total": money(order.grand_total, order.currency),
    }


class OrderDetailResponseSerializer(serializers.Serializer):
    """Response shape for order detail and the polling endpoint."""

    reference = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    payment_status = serializers.CharField()
    payment_method = serializers.CharField()
    fulfilment_type = serializers.CharField()
    placed_at = serializers.DateTimeField(allow_null=True)
    estimated_ready_at = serializers.DateTimeField(allow_null=True)
    estimated_delivery_at = serializers.DateTimeField(allow_null=True)
    timeline = serializers.ListField(child=serializers.DictField())
    items = serializers.ListField(child=serializers.DictField())
    delivery_address = serializers.DictField(allow_null=True)
    totals = TotalsSerializer()
    promo_code = serializers.CharField(allow_blank=True)
    customer_note = serializers.CharField(allow_blank=True)
    can_cancel = serializers.BooleanField()
    rider = serializers.DictField(allow_null=True)
    guest_token = serializers.CharField(required=False)

    class Meta:
        ref_name = "OrderDetail"


class KDSTicketSerializer(serializers.Serializer):
    """One kitchen ticket."""

    reference = serializers.CharField()
    status = serializers.CharField()
    placed_at = serializers.DateTimeField()
    elapsed_seconds = serializers.IntegerField()
    is_late = serializers.BooleanField()
    fulfilment_type = serializers.CharField()
    zone = serializers.CharField(allow_blank=True)
    payment_status = serializers.CharField()
    payment_method = serializers.CharField()
    requires_cash_collection = serializers.BooleanField()
    items = serializers.ListField(child=serializers.DictField())
    customer_note = serializers.CharField(allow_blank=True)
    customer = serializers.DictField()
    grand_total = MoneySerializer()

    class Meta:
        ref_name = "KDSTicket"


class KDSQueueSerializer(serializers.Serializer):
    orders = KDSTicketSerializer(many=True)

    class Meta:
        ref_name = "KDSQueue"


class KDSSummarySerializer(serializers.Serializer):
    counts = serializers.DictField(child=serializers.IntegerField())
    todays_revenue = serializers.DictField()
    open_tickets = serializers.IntegerField()

    class Meta:
        ref_name = "KDSSummary"


class RiderAssignmentSerializer(serializers.Serializer):
    order = serializers.CharField()
    rider = serializers.DictField()
    assigned_at = serializers.DateTimeField()

    class Meta:
        ref_name = "RiderAssignment"


class ItemAvailabilitySerializer(serializers.Serializer):
    slug = serializers.CharField()
    is_available_now = serializers.BooleanField()

    class Meta:
        ref_name = "ItemAvailability"
