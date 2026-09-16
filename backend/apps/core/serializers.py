"""Core serializers."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.serializers import MoneyField
from apps.core.models import (
    Award,
    Branch,
    HolidayOverride,
    LegalPage,
    OpeningHours,
    SiteSettings,
    TeamMember,
)
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


class BankTransferSerializer(serializers.Serializer):
    bank_name = serializers.CharField()
    account_name = serializers.CharField()
    account_number = serializers.CharField()

    class Meta:
        ref_name = "BankTransferDetails"


class BranchSerializer(serializers.ModelSerializer):
    """Everything the frontend needs to decide whether ordering is possible."""

    min_order_value = MoneyField()
    free_delivery_threshold = MoneyField()
    is_open_now = serializers.BooleanField(read_only=True)
    can_accept_orders = serializers.BooleanField(read_only=True)
    next_opens_at = serializers.SerializerMethodField()
    bank_transfer = serializers.SerializerMethodField()

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
            "bank_transfer",
        )
        read_only_fields = fields

    @extend_schema_field(BankTransferSerializer(allow_null=True))
    def get_bank_transfer(self, obj: Branch) -> dict[str, str] | None:
        """Null when transfer is switched off, so the checkout does not offer it."""
        if not obj.accepts_bank_transfer:
            return None
        return {
            "bank_name": obj.bank_name,
            "account_name": obj.bank_account_name,
            "account_number": obj.bank_account_number,
        }

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_next_opens_at(self, obj: Branch) -> Any:
        if obj.is_open_now:
            return None
        moment = next_opening(obj)
        return moment.isoformat() if moment else None


class SiteSettingsSerializer(serializers.ModelSerializer):
    """What `/core/settings/` publishes to anyone who asks.

    An explicit allowlist, not ``exclude``. With ``exclude`` this endpoint served
    ``support_email`` and ``orders_email`` — the internal mailboxes alerts are
    delivered to — unauthenticated, and every field added to the model later
    would have been published automatically by the same omission. Adding a field
    to this list is now a deliberate act.
    """

    class Meta:
        model = SiteSettings
        fields = (
            "site_name",
            "tagline",
            "meta_description",
            "instagram_url",
            "facebook_url",
            "twitter_url",
            "tiktok_url",
            "established_year",
            "stat_customers",
            "stat_dishes",
            "stat_years",
            "stat_rating",
        )
        read_only_fields = fields


class OpeningHoursResponseSerializer(serializers.Serializer):
    """Response envelope for ``GET /core/opening-hours/``.

    Declared explicitly so the generated OpenAPI schema — and therefore the
    frontend's generated types — describe this endpoint accurately.
    """

    is_open_now = serializers.BooleanField()
    timezone = serializers.CharField()
    hours = OpeningHoursSerializer(many=True)
    overrides = HolidayOverrideSerializer(many=True)


class LegalPageSerializer(serializers.ModelSerializer):
    """A policy page as customers read it."""

    class Meta:
        model = LegalPage
        fields = ("slug", "title", "body", "version", "effective_from", "updated_at")
        read_only_fields = fields


class LegalPageSummarySerializer(serializers.ModelSerializer):
    """The index: enough to build a footer, without shipping five documents."""

    class Meta:
        model = LegalPage
        fields = ("slug", "title", "version", "effective_from")
        read_only_fields = fields


class TeamMemberSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = TeamMember
        fields = ("name", "role", "bio", "photo_url")
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj: TeamMember) -> str | None:
        return obj.photo.url if obj.photo else None


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = ("title", "awarded_by", "year", "url")
        read_only_fields = fields
