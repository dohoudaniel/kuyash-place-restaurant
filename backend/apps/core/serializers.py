"""Core serializers."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.serializers import MoneyField
from apps.core.models import Branch, HolidayOverride, OpeningHours, SiteSettings
from apps.core.selectors import next_opening


class OpeningHoursSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = OpeningHours
        fields = ("weekday", "weekday_display", "service", "opens_at", "closes_at", "is_closed")


class HolidayOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayOverride
        fields = ("date", "is_closed", "opens_at", "closes_at", "note")


class BranchSerializer(serializers.ModelSerializer):
    """Everything the frontend needs to decide whether ordering is possible."""

    min_order_value = MoneyField()
    free_delivery_threshold = MoneyField()
    is_open_now = serializers.BooleanField(read_only=True)
    can_accept_orders = serializers.BooleanField(read_only=True)
    next_opens_at = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = (
            "id",
            "name",
            "slug",
            "phone",
            "whatsapp",
            "email",
            "address_line",
            "city",
            "state",
            "latitude",
            "longitude",
            "timezone",
            "currency",
            "prices_include_vat",
            "vat_rate_bps",
            "service_charge_bps",
            "is_accepting_orders",
            "is_open_now",
            "can_accept_orders",
            "next_opens_at",
            "min_order_value",
            "free_delivery_threshold",
            "default_prep_minutes",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_next_opens_at(self, obj: Branch) -> Any:
        if obj.is_open_now:
            return None
        moment = next_opening(obj)
        return moment.isoformat() if moment else None


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ("id", "created_at", "updated_at")


class OpeningHoursResponseSerializer(serializers.Serializer):
    """Response envelope for ``GET /core/opening-hours/``.

    Declared explicitly so the generated OpenAPI schema — and therefore the
    frontend's generated types — describe this endpoint accurately.
    """

    is_open_now = serializers.BooleanField()
    timezone = serializers.CharField()
    hours = OpeningHoursSerializer(many=True)
    overrides = HolidayOverrideSerializer(many=True)
