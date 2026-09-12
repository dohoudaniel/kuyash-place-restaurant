"""Catering routes."""

from __future__ import annotations

from django.urls import path

from apps.catering.views import (
    EnquiryCreateView,
    EnquiryDetailView,
    OverdueEnquiriesView,
    PackageListView,
)

app_name = "catering"

urlpatterns = [
    path("packages/", PackageListView.as_view(), name="packages"),
    path("enquiries/", EnquiryCreateView.as_view(), name="enquiry-create"),
    path("enquiries/overdue/", OverdueEnquiriesView.as_view(), name="enquiries-overdue"),
    path("enquiries/<str:reference>/", EnquiryDetailView.as_view(), name="enquiry-detail"),
]
