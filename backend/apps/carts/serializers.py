"""Cart serializers.

Output only: there is no field anywhere here through which a client can send a
price, a discount or a total.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.common.money import format_money
from apps.common.serializers import MoneySerializer, TotalsSerializer


def money(amount: int, currency: str = "NGN") -> dict[str, Any]:
    return {"amount": amount, "currency": currency, "display": format_money(amount, currency)}


class ModifierChoiceSerializer(serializers.Serializer):
    """One chosen option. Typed, so the generated client knows the shape."""

    modifier = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=20, default=1)

    class Meta:
        ref_name = "ModifierChoice"


class AddItemSerializer(serializers.Serializer):
    """Input for adding a line. Note the absence of any price field."""

    menu_item = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)
    variant = serializers.UUIDField(required=False, allow_null=True)
    modifiers = ModifierChoiceSerializer(many=True, required=False, default=list)
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


class ItemQuoteInputSerializer(serializers.Serializer):
    """A dish configuration to price. The same fields as adding to the cart."""

    menu_item = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)
    variant = serializers.UUIDField(required=False, allow_null=True)
    modifiers = ModifierChoiceSerializer(many=True, required=False, default=list)

    class Meta:
        ref_name = "ItemQuoteInput"


class ItemQuoteSerializer(serializers.Serializer):
    menu_item = serializers.SlugField()
    quantity = serializers.IntegerField()
    unit_price = MoneySerializer()
    line_total = MoneySerializer()
    is_available_now = serializers.BooleanField(
        help_text="False outside the dish's serving window; it can be quoted but not added."
    )

    class Meta:
        ref_name = "ItemQuote"


class _PriceFragmentSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    display = serializers.CharField()

    class Meta:
        ref_name = "PriceFragment"


class CartMenuItemRefSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    name = serializers.CharField()
    image_url = serializers.CharField(allow_null=True)

    class Meta:
        ref_name = "CartMenuItemRef"


class CartLineModifierSerializer(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    price_delta = MoneySerializer()

    class Meta:
        ref_name = "CartLineModifier"


class CartLineSerializer(serializers.Serializer):
    id = serializers.CharField()
    menu_item = CartMenuItemRefSerializer()
    variant_name = serializers.CharField(allow_blank=True)
    quantity = serializers.IntegerField()
    modifiers = CartLineModifierSerializer(many=True)
    unit_price = MoneySerializer()
    line_subtotal = MoneySerializer()
    discount = MoneySerializer()
    vat = MoneySerializer()
    special_instructions = serializers.CharField(allow_blank=True)
    is_available = serializers.BooleanField()
    unavailable_reason = serializers.CharField(allow_blank=True)

    class Meta:
        ref_name = "CartLine"


class CartChangeSerializer(serializers.Serializer):
    item = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField(help_text="price_increased | price_reduced")
    old = _PriceFragmentSerializer(required=False)
    new = _PriceFragmentSerializer(required=False)

    class Meta:
        ref_name = "CartChange"


class CartUnavailableSerializer(serializers.Serializer):
    item = serializers.CharField()
    name = serializers.CharField()
    reason = serializers.CharField()

    class Meta:
        ref_name = "CartUnavailable"


class CartBlockerSerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text=(
            "address_required | outside_delivery_area | below_minimum_order | "
            "item_unavailable | cart_empty | branch_closed"
        )
    )
    detail = serializers.CharField()

    class Meta:
        ref_name = "CartBlocker"


class CartResponseSerializer(serializers.Serializer):
    """Documents the cart response shape for the generated schema."""

    id = serializers.UUIDField()
    fulfilment_type = serializers.CharField()
    delivery_address = serializers.UUIDField(allow_null=True)
    items = CartLineSerializer(many=True)
    item_count = serializers.IntegerField(help_text="Total quantity across lines, for badges.")
    totals = TotalsSerializer()
    promo_code = serializers.CharField(allow_blank=True)
    prices_include_vat = serializers.BooleanField()
    vat_note = serializers.CharField(allow_blank=True)
    delivery_note = serializers.CharField(allow_blank=True)
    estimated_minutes = serializers.IntegerField(allow_null=True)
    changes = CartChangeSerializer(many=True)
    unavailable = CartUnavailableSerializer(many=True)
    blockers = CartBlockerSerializer(many=True)
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
        "item_count": sum(line.quantity for line in priced.lines),
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
