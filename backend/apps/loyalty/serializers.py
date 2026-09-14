"""Loyalty serializers."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.carts.serializers import money
from apps.common.serializers import MoneySerializer
from apps.loyalty import services
from apps.loyalty.models import (
    LedgerEntryType,
    LoyaltyAccount,
    LoyaltyTier,
    PointsLedgerEntry,
    Reward,
    RewardType,
)


class TierSerializer(serializers.ModelSerializer):
    multiplier = serializers.SerializerMethodField()
    earn_rate = serializers.SerializerMethodField()
    benefits = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = LoyaltyTier
        fields = (
            "name",
            "min_points",
            "multiplier",
            "earn_rate",
            "birthday_points",
            "benefits",
            "colour",
        )
        read_only_fields = fields

    def get_multiplier(self, obj: LoyaltyTier) -> str:
        return services.multiplier_label(obj.points_multiplier_bps)

    def get_earn_rate(self, obj: LoyaltyTier) -> str:
        return services.earn_rate_label(obj.points_multiplier_bps)


class ProgrammeSerializer(serializers.Serializer):
    tiers = TierSerializer(many=True)
    base_earn_rate = serializers.CharField()
    expiry_inactive_days = serializers.IntegerField()

    class Meta:
        ref_name = "LoyaltyProgramme"


class NextTierSerializer(serializers.Serializer):
    name = serializers.CharField()
    min_points = serializers.IntegerField()
    points_to_go = serializers.IntegerField()

    class Meta:
        ref_name = "LoyaltyNextTier"


class AppliedRewardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()

    class Meta:
        ref_name = "LoyaltyAppliedReward"


class AccountSerializer(serializers.ModelSerializer):
    tier = TierSerializer(read_only=True, allow_null=True)
    next_tier = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    earn_rate = serializers.SerializerMethodField()
    applied_reward = serializers.SerializerMethodField()
    birthday_on_file = serializers.SerializerMethodField()

    class Meta:
        model = LoyaltyAccount
        fields = (
            "points_balance",
            "lifetime_points",
            "tier",
            "next_tier",
            "progress_percent",
            "earn_rate",
            "applied_reward",
            "birthday_on_file",
            "is_closed",
        )
        read_only_fields = fields

    @extend_schema_field(NextTierSerializer(allow_null=True))
    def get_next_tier(self, obj: LoyaltyAccount) -> dict[str, Any] | None:
        tier = services.next_tier(obj)
        if tier is None:
            return None
        return {
            "name": tier.name,
            "min_points": tier.min_points,
            "points_to_go": tier.min_points - max(obj.lifetime_points, 0),
        }

    def get_progress_percent(self, obj: LoyaltyAccount) -> int:
        """How far from the current tier's floor to the next tier's."""
        upcoming = services.next_tier(obj)
        if upcoming is None:
            return 100
        floor = obj.tier.min_points if obj.tier else 0
        span = upcoming.min_points - floor
        return (
            max(0, min(100, (max(obj.lifetime_points, 0) - floor) * 100 // span)) if span else 100
        )

    def get_earn_rate(self, obj: LoyaltyAccount) -> str:
        return services.earn_rate_label(
            obj.tier.points_multiplier_bps if obj.tier else services.BASE_MULTIPLIER_BPS
        )

    @extend_schema_field(AppliedRewardSerializer(allow_null=True))
    def get_applied_reward(self, obj: LoyaltyAccount) -> dict[str, str] | None:
        cart = self.context.get("cart")
        reward = getattr(cart, "loyalty_reward", None)
        return {"id": str(reward.pk), "name": reward.name} if reward else None

    def get_birthday_on_file(self, obj: LoyaltyAccount) -> bool:
        profile = getattr(obj.user, "profile", None)
        return bool(profile and profile.date_of_birth)


class RewardMenuItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()

    class Meta:
        ref_name = "RewardMenuItem"


class RewardSerializer(serializers.ModelSerializer):
    reward_type = serializers.ChoiceField(choices=RewardType.choices, read_only=True)
    reward_type_display = serializers.CharField(source="get_reward_type_display", read_only=True)
    # Not get_value: that name is DRF's own Field.get_value.
    value = serializers.SerializerMethodField(method_name="get_money_value")
    min_order_value = serializers.SerializerMethodField()
    menu_item = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    affordable = serializers.SerializerMethodField()
    points_short = serializers.SerializerMethodField()

    class Meta:
        model = Reward
        fields = (
            "id",
            "name",
            "description",
            "points_cost",
            "reward_type",
            "reward_type_display",
            "value",
            "min_order_value",
            "menu_item",
            "in_stock",
            "affordable",
            "points_short",
        )
        read_only_fields = fields

    def _balance(self) -> int | None:
        return self.context.get("balance")

    @extend_schema_field(MoneySerializer(allow_null=True))
    def get_money_value(self, obj: Reward) -> dict[str, Any] | None:
        return money(obj.value) if obj.reward_type == RewardType.DISCOUNT else None

    @extend_schema_field(MoneySerializer(allow_null=True))
    def get_min_order_value(self, obj: Reward) -> dict[str, Any] | None:
        return money(obj.min_order_value) if obj.min_order_value else None

    @extend_schema_field(RewardMenuItemSerializer(allow_null=True))
    def get_menu_item(self, obj: Reward) -> dict[str, str] | None:
        item = obj.menu_item
        return {"slug": item.slug, "name": item.name} if item else None

    def get_in_stock(self, obj: Reward) -> bool:
        return services.reward_is_available(obj)

    @extend_schema_field(serializers.BooleanField(allow_null=True))
    def get_affordable(self, obj: Reward) -> bool | None:
        """Null for visitors who are not signed in."""
        balance = self._balance()
        return None if balance is None else balance >= obj.points_cost

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_points_short(self, obj: Reward) -> int | None:
        balance = self._balance()
        return None if balance is None else max(obj.points_cost - balance, 0)


class LedgerEntrySerializer(serializers.ModelSerializer):
    entry_type = serializers.ChoiceField(choices=LedgerEntryType.choices, read_only=True)
    entry_type_display = serializers.CharField(source="get_entry_type_display", read_only=True)
    order_reference = serializers.SerializerMethodField()

    class Meta:
        model = PointsLedgerEntry
        fields = (
            "id",
            "entry_type",
            "entry_type_display",
            "points",
            "description",
            "order_reference",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_order_reference(self, obj: PointsLedgerEntry) -> str | None:
        return obj.order.reference if obj.order else None


def programme_payload() -> dict[str, Any]:
    return {
        "tiers": TierSerializer(LoyaltyTier.objects.all(), many=True).data,
        "base_earn_rate": services.earn_rate_label(),
        "expiry_inactive_days": settings.LOYALTY_EXPIRY_INACTIVE_DAYS,
    }
