"""Order routes."""

from __future__ import annotations

from django.urls import path

from apps.orders.reorder_views import ReceiptView, ReorderView
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
    path("<str:reference>/reorder/", ReorderView.as_view(), name="reorder"),
    path("<str:reference>/receipt/", ReceiptView.as_view(), name="receipt"),
]
