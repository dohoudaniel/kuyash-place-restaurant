"""Gallery admin — where staff upload and arrange photos."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import format_html

from apps.core.selectors import get_current_branch
from apps.gallery.models import GalleryImage, GalleryTag


@admin.register(GalleryTag)
class GalleryTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "title",
        "category",
        "is_featured",
        "is_active",
        "display_order",
    )
    list_display_links = ("thumbnail", "title")
    list_editable = ("is_featured", "is_active", "display_order")
    list_filter = ("category", "is_featured", "is_active", "tags")
    search_fields = ("title", "description", "alt_text")
    filter_horizontal = ("tags",)
    readonly_fields = ("preview", "created_at", "updated_at")
    fields = (
        "branch",
        "category",
        "title",
        "description",
        "image",
        "preview",
        "alt_text",
        "tags",
        "display_order",
        "is_featured",
        "is_active",
        "created_at",
        "updated_at",
    )

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("branch", str(get_current_branch().pk))
        return initial

    @admin.display(description="Photo")
    def thumbnail(self, obj: GalleryImage) -> str:
        return format_html(
            '<img src="{}" alt="" '
            'style="height:48px;width:48px;object-fit:cover;border-radius:6px">',
            obj.image.url,
        )

    @admin.display(description="Preview")
    def preview(self, obj: GalleryImage) -> str:
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:240px;border-radius:8px">', obj.image.url
        )
