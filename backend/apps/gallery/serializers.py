"""Gallery serializers."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.gallery.models import GalleryCategory, GalleryImage, GalleryTag


class GalleryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryTag
        fields = ("slug", "name")


class GalleryImageSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=GalleryCategory.choices, read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    image_url = serializers.SerializerMethodField()
    alt_text = serializers.SerializerMethodField()
    tags = GalleryTagSerializer(many=True, read_only=True)

    class Meta:
        model = GalleryImage
        fields: tuple[str, ...] = (
            "id",
            "category",
            "category_display",
            "title",
            "description",
            "image_url",
            "alt_text",
            "tags",
            "is_featured",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.URLField())
    def get_image_url(self, obj: GalleryImage) -> str:
        return obj.image.url

    def get_alt_text(self, obj: GalleryImage) -> str:
        return obj.alt_text or obj.title


class GalleryImageDetailSerializer(GalleryImageSerializer):
    """One photo plus its neighbours, so a shared link opens a working lightbox."""

    previous_id = serializers.UUIDField(allow_null=True, read_only=True)
    next_id = serializers.UUIDField(allow_null=True, read_only=True)

    class Meta(GalleryImageSerializer.Meta):
        fields = (*GalleryImageSerializer.Meta.fields, "previous_id", "next_id")
        read_only_fields = fields
