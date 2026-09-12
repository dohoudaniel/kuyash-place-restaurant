"""Order routes."""

from __future__ import annotations

from django.urls import path

from apps.orders.views import (
    OrderCancelView,
    OrderCreateListView,
    OrderDetailView,
    OrderHistoryView,
)

app_name = "orders"

urlpatterns = [
    path("", OrderCreateListView.as_view(), name="create"),
    path("mine/", OrderHistoryView.as_view(), name="history"),
    path("<str:reference>/", OrderDetailView.as_view(), name="detail"),
    path("<str:reference>/cancel/", OrderCancelView.as_view(), name="cancel"),
]
