"""Cart serializers.

Output only: there is no field anywhere here through which a client can send a
price, a discount or a total.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.common.money import format_money
from apps.common.serializers import TotalsSerializer


def money(amount: int, currency: str = "NGN") -> dict[str, Any]:
    return {"amount": amount, "currency": currency, "display": format_money(amount, currency)}


class AddItemSerializer(serializers.Serializer):
    """Input for adding a line. Note the absence of any price field."""

    menu_item = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)
    variant = serializers.UUIDField(required=False, allow_null=True)
    modifiers = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    special_instructions = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=99, required=False)
    special_instructions = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PromoSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class FulfilmentSerializer(serializers.Serializer):
    fulfilment_type = serializers.ChoiceField(choices=["delivery", "pickup"], required=False)
    delivery_address = serializers.UUIDField(required=False, allow_null=True)
    tip = serializers.IntegerField(min_value=0, required=False, help_text="Gratuity in kobo.")


class CartResponseSerializer(serializers.Serializer):
    """Documents the cart response shape for the generated schema."""

    id = serializers.UUIDField()
    fulfilment_type = serializers.CharField()
    items = serializers.ListField(child=serializers.DictField())
    totals = TotalsSerializer()
    promo_code = serializers.CharField(allow_blank=True)
    vat_note = serializers.CharField(allow_blank=True)
    delivery_note = serializers.CharField(allow_blank=True)
    estimated_minutes = serializers.IntegerField(allow_null=True)
    changes = serializers.ListField(child=serializers.DictField())
    unavailable = serializers.ListField(child=serializers.DictField())
    blockers = serializers.ListField(child=serializers.DictField())
    can_checkout = serializers.BooleanField()

    class Meta:
        ref_name = "Cart"


def serialise_cart(cart: Any, priced: Any) -> dict[str, Any]:
    """Render a priced cart.

    Every money value is a ``{amount, currency, display}`` object, so the client
    renders ``display`` and performs no arithmetic of its own.
    """
    currency = priced.currency

    return {
        "id": str(cart.pk),
        "fulfilment_type": cart.fulfilment_type,
        "delivery_address": str(cart.delivery_address_id) if cart.delivery_address_id else None,
        "items": [
            {
                "id": line.cart_item_id,
                "menu_item": {
                    "slug": line.slug,
                    "name": line.name,
                    "image_url": line.image_url,
                },
                "variant_name": line.variant_name,
                "quantity": line.quantity,
                "modifiers": [
                    {
                        "name": modifier.name,
                        "quantity": modifier.quantity,
                        "price_delta": money(modifier.price_delta, currency),
                    }
                    for modifier in line.modifiers
                ],
                "unit_price": money(line.unit_price, currency),
                "line_subtotal": money(line.line_subtotal, currency),
                "discount": money(line.discount, currency),
                "vat": money(line.vat, currency),
                "special_instructions": line.special_instructions,
                "is_available": line.is_available,
                "unavailable_reason": line.unavailable_reason,
            }
            for line in priced.lines
        ],
        "promo_code": priced.promo_code,
        "totals": {
            "subtotal": money(priced.subtotal, currency),
            "discount": money(priced.discount_total, currency),
            "delivery_fee": money(priced.delivery_fee, currency),
            "service_charge": money(priced.service_charge, currency),
            "vat": money(priced.vat_total, currency),
            "tip": money(priced.tip, currency),
            "grand_total": money(priced.grand_total, currency),
        },
        "prices_include_vat": priced.prices_include_vat,
        "vat_note": priced.vat_note,
        "delivery_note": priced.delivery_note,
        "estimated_minutes": priced.estimated_minutes,
        "changes": priced.changes,
        "unavailable": priced.unavailable,
        "blockers": priced.blockers,
        "can_checkout": priced.can_checkout,
    }
