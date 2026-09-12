"""Catalogue serializers.

Every price crosses the wire as a money object. There is no endpoint that
accepts a price — see docs/ARCHITECTURE.md §8.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import (
    Category,
    DietaryTag,
    MenuItem,
    MenuItemImage,
    Modifier,
    ModifierGroup,
    Variant,
)
from apps.common.serializers import MONEY_SCHEMA, MoneyField


class DietaryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietaryTag
        fields = ("slug", "name", "icon", "is_allergen")


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ("id", "slug", "name", "emoji", "description", "display_order", "item_count")


class MenuItemImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MenuItemImage
        fields = ("url", "alt_text", "is_primary")

    @extend_schema_field(serializers.URLField())
    def get_url(self, obj: MenuItemImage) -> str:
        return obj.image.url if obj.image else ""


class VariantSerializer(serializers.ModelSerializer):
    price_delta = MoneyField()

    class Meta:
        model = Variant
        fields = ("id", "name", "price_delta", "is_default")


class ModifierSerializer(serializers.ModelSerializer):
    price_delta = MoneyField()

    class Meta:
        model = Modifier
        fields = ("id", "name", "price_delta", "is_default", "is_available")


class ModifierGroupSerializer(serializers.ModelSerializer):
    modifiers = ModifierSerializer(many=True, read_only=True)
    is_required = serializers.BooleanField(read_only=True)

    class Meta:
        model = ModifierGroup
        fields = (
            "id",
            "name",
            "description",
            "min_select",
            "max_select",
            "is_required",
            "modifiers",
        )


class _MenuItemBaseSerializer(serializers.ModelSerializer):
    """Fields common to the list and detail shapes.

    ``category`` is declared by the subclasses, not here: the list shape needs a
    bare slug while the detail shape nests the whole category, and redeclaring a
    field with a different type in a subclass is a type error waiting to happen.
    """

    price = MoneyField(source="base_price")
    compare_at_price = MoneyField()
    image_url = serializers.SerializerMethodField()
    dietary_tags = DietaryTagSerializer(many=True, read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "price",
            "compare_at_price",
            "image_url",
            "dietary_tags",
            "average_rating",
            "review_count",
            "prep_time_minutes",
            "is_featured",
            "is_available",
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image_url(self, obj: MenuItem) -> str | None:
        primary = next((image for image in obj.images.all() if image.is_primary), None)
        image = primary or next(iter(obj.images.all()), None)
        return image.image.url if image and image.image else None

    @extend_schema_field(serializers.BooleanField())
    def get_is_available(self, obj: MenuItem) -> bool:
        return obj.available_at()


class MenuItemListSerializer(_MenuItemBaseSerializer):
    """Compact shape for grids and carousels."""

    category = serializers.CharField(source="category.slug", read_only=True)

    class Meta(_MenuItemBaseSerializer.Meta):
        fields = [*_MenuItemBaseSerializer.Meta.fields, "category"]


class MenuItemDetailSerializer(_MenuItemBaseSerializer):
    """Full shape, including everything needed to configure a line."""

    category = CategorySerializer(read_only=True)
    images = MenuItemImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)

    class Meta(_MenuItemBaseSerializer.Meta):
        fields = [
            *_MenuItemBaseSerializer.Meta.fields,
            "category",
            "images",
            "variants",
            "modifier_groups",
            "calories",
            "allergen_note",
            "tax_class",
            "published_at",
        ]

    @extend_schema_field(VariantSerializer(many=True))
    def get_variants(self, obj: MenuItem) -> list[dict[str, Any]]:
        active = [variant for variant in obj.variants.all() if variant.is_active]
        return list(VariantSerializer(active, many=True).data)


class MenuItemPriceSerializer(serializers.Serializer):
    """Documents the money envelope for schema consumers."""

    amount = serializers.IntegerField()
    currency = serializers.CharField()
    display = serializers.CharField()

    class Meta:
        ref_name = "Money"


__all__ = [
    "MONEY_SCHEMA",
    "CategorySerializer",
    "DietaryTagSerializer",
    "MenuItemDetailSerializer",
    "MenuItemListSerializer",
    "ModifierGroupSerializer",
    "VariantSerializer",
]
