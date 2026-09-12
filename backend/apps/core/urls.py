"""Core routes."""

from __future__ import annotations

from django.urls import path

from apps.core.views import (
    BranchView,
    LegalPageDetailView,
    LegalPageListView,
    OpeningHoursView,
    SiteSettingsView,
)

app_name = "core"

urlpatterns = [
    path("branch/", BranchView.as_view(), name="branch"),
    path("opening-hours/", OpeningHoursView.as_view(), name="opening-hours"),
    path("settings/", SiteSettingsView.as_view(), name="settings"),
    path("legal/", LegalPageListView.as_view(), name="legal-list"),
    path("legal/<slug:slug>/", LegalPageDetailView.as_view(), name="legal-detail"),
]
