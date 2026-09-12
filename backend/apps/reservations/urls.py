"""Reservation routes."""

from __future__ import annotations

from django.urls import path

from apps.reservations.views import (
    AreaListView,
    AvailabilityView,
    MyReservationsView,
    ReservationCancelView,
    ReservationCreateView,
    ReservationDetailView,
    TodaysBookView,
)

app_name = "reservations"

urlpatterns = [
    path("areas/", AreaListView.as_view(), name="areas"),
    path("availability/", AvailabilityView.as_view(), name="availability"),
    path("mine/", MyReservationsView.as_view(), name="mine"),
    path("book/", TodaysBookView.as_view(), name="todays-book"),
    path("", ReservationCreateView.as_view(), name="create"),
    path("<str:reference>/", ReservationDetailView.as_view(), name="detail"),
    path("<str:reference>/cancel/", ReservationCancelView.as_view(), name="cancel"),
]
