"""Delivery serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import MoneyField
from apps.delivery.models import DeliveryZone


class DeliveryZoneSerializer(serializers.ModelSerializer):
    fee = MoneyField()
    min_order_value = MoneyField()

    class Meta:
        model = DeliveryZone
        fields = ("id", "slug", "name", "fee", "min_order_value", "estimated_minutes")
        read_only_fields = fields
