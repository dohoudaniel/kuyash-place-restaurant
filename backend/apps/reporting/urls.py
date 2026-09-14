"""Report routes."""

from __future__ import annotations

from django.urls import path

from apps.reporting.views import (
    PeakHoursReportView,
    PopularItemsReportView,
    RiderReportView,
    SalesReportView,
)

app_name = "reporting"

urlpatterns = [
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("items/", PopularItemsReportView.as_view(), name="items"),
    path("peak-hours/", PeakHoursReportView.as_view(), name="peak-hours"),
    path("riders/", RiderReportView.as_view(), name="riders"),
]
