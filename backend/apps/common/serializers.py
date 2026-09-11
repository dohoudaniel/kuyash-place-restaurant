"""Serializer primitives."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.money import DEFAULT_CURRENCY, format_money

MONEY_SCHEMA = {
    "type": "object",
    "nullable": True,
    "required": ["amount", "currency", "display"],
    "properties": {
        "amount": {
            "type": "integer",
            "description": (
                "Integer kobo. ₦1.00 = 100. Render `display`; never do arithmetic on this."
            ),
        },
        "currency": {"type": "string", "example": "NGN"},
        "display": {"type": "string", "example": "₦12,500.00"},
    },
}


class MoneySerializer(serializers.Serializer):
    """Read-only representation of a money amount.

    Always emits ``{amount, currency, display}``. ``amount`` is integer kobo;
    ``display`` is the formatted string clients render. Clients never format
    currency themselves and never do arithmetic on ``amount``.
    """

    amount = serializers.IntegerField(read_only=True, help_text="Integer kobo. ₦1.00 = 100.")
    currency = serializers.CharField(read_only=True, default=DEFAULT_CURRENCY)
    display = serializers.CharField(read_only=True, help_text="Formatted, e.g. ₦12,500.00")


@extend_schema_field(MONEY_SCHEMA)
class MoneyField(serializers.Field):
    """Serializes an integer-kobo model field into the money wire format.

    Read-only by design: a client must never be able to send a price.
    """

    def get_attribute(self, instance: Any) -> Any:
        # Allow None through to to_representation rather than skipping the field.
        return serializers.Field.get_attribute(self, instance)

    def __init__(self, *args: Any, currency: str = DEFAULT_CURRENCY, **kwargs: Any) -> None:
        kwargs["read_only"] = True
        self.currency = currency
        super().__init__(*args, **kwargs)

    def to_representation(self, value: int | None) -> dict[str, Any] | None:
        # NULL stays NULL. A threshold of "none" must not arrive as ₦0.00, which
        # the client would read as "always free".
        if value is None:
            return None
        amount = int(value)
        return {
            "amount": amount,
            "currency": self.currency,
            "display": format_money(amount, self.currency),
        }

    def to_internal_value(self, data: Any) -> Any:  # pragma: no cover - read-only field
        raise serializers.ValidationError("Money values are server-authoritative and read-only.")
