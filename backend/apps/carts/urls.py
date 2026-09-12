"""Cart routes."""

from __future__ import annotations

from django.urls import path

from apps.carts.views import (
    CartFulfilmentView,
    CartItemDetailView,
    CartItemsView,
    CartMergeView,
    CartPromoView,
    CartView,
)

app_name = "carts"

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemsView.as_view(), name="items"),
    path("items/<uuid:pk>/", CartItemDetailView.as_view(), name="item-detail"),
    path("promo/", CartPromoView.as_view(), name="promo"),
    path("fulfilment/", CartFulfilmentView.as_view(), name="fulfilment"),
    path("merge/", CartMergeView.as_view(), name="merge"),
]
