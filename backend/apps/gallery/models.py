"""Gallery photographs.

Replaces a hardcoded array of 20 entries in ``app/gallery/page.tsx`` whose
image keys had no files behind them, so every tile rendered a placeholder icon.
Photos are uploaded by staff and served from Supabase Storage in production.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel

#: Large enough for a good phone photo, small enough to keep the page fast.
MAX_IMAGE_BYTES = 10 * 1024 * 1024

#: Raster formats only. SVG is refused: it can carry script, and these files
#: are served from a public bucket.
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


def validate_image_size(file: Any) -> None:
    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError(
            f"Photos must be {MAX_IMAGE_BYTES // (1024 * 1024)} MB or smaller.",
            code="image_too_large",
        )


class GalleryCategory(models.TextChoices):
    """The filter tabs already on the gallery page."""

    FOOD = "food", "Food"
    INTERIOR = "interior", "Interior"
    EVENTS = "events", "Events"
    TEAM = "team", "Team"
    AMBIANCE = "ambiance", "Ambiance"


class GalleryTag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class GalleryImage(TimeStampedModel, SoftDeleteModel):
    branch = models.ForeignKey(
        "core.Branch", on_delete=models.CASCADE, related_name="gallery_images"
    )
    category = models.CharField(max_length=20, choices=GalleryCategory.choices, db_index=True)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to="gallery/",
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS), validate_image_size],
    )
    alt_text = models.CharField(
        max_length=200, blank=True, help_text="Describe the photo for screen readers."
    )
    tags = models.ManyToManyField(GalleryTag, blank=True, related_name="images")
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [models.Index(fields=["branch", "is_active", "category"])]

    def __str__(self) -> str:
        return self.title
