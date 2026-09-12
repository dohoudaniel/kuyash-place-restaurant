"""Support routes."""

from __future__ import annotations

from django.urls import path

from apps.support.views import (
    ContactView,
    FaqListView,
    MyTicketsView,
    OpenTicketsView,
    TicketDetailView,
)

app_name = "support"

urlpatterns = [
    path("contact/", ContactView.as_view(), name="contact"),
    path("faq/", FaqListView.as_view(), name="faq"),
    path("tickets/", MyTicketsView.as_view(), name="my-tickets"),
    path("tickets/open/", OpenTicketsView.as_view(), name="open-tickets"),
    path("tickets/<str:reference>/", TicketDetailView.as_view(), name="ticket-detail"),
]
