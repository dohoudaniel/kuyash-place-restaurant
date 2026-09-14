"""Core routes."""

from __future__ import annotations

from django.urls import path

from apps.core.views import (
    AwardListView,
    BranchView,
    LegalPageDetailView,
    LegalPageListView,
    OpeningHoursView,
    SiteSettingsView,
    TeamListView,
)

app_name = "core"

urlpatterns = [
    path("branch/", BranchView.as_view(), name="branch"),
    path("opening-hours/", OpeningHoursView.as_view(), name="opening-hours"),
    path("settings/", SiteSettingsView.as_view(), name="settings"),
    path("legal/", LegalPageListView.as_view(), name="legal-list"),
    path("team/", TeamListView.as_view(), name="team"),
    path("awards/", AwardListView.as_view(), name="awards"),
    path("legal/<slug:slug>/", LegalPageDetailView.as_view(), name="legal-detail"),
]
