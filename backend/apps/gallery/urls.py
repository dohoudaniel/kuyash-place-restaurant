"""Gallery routes."""

from __future__ import annotations

from django.urls import path

from apps.gallery.views import GalleryDetailView, GalleryListView

app_name = "gallery"

urlpatterns = [
    path("", GalleryListView.as_view(), name="list"),
    path("<uuid:image_id>/", GalleryDetailView.as_view(), name="detail"),
]
