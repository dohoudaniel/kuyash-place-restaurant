"""Catalogue routes."""

from __future__ import annotations

from django.urls import path

from apps.catalog.views import (
    CategoryListView,
    DietaryTagListView,
    FeaturedItemsView,
    MenuItemDetailView,
    MenuItemListView,
)
from apps.catalog.wishlist_views import (
    WishlistItemView,
    WishlistSyncView,
    WishlistView,
)

app_name = "catalog"

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("dietary-tags/", DietaryTagListView.as_view(), name="dietary-tags"),
    path("featured/", FeaturedItemsView.as_view(), name="featured"),
    path("items/", MenuItemListView.as_view(), name="items"),
    path("items/<slug:slug>/", MenuItemDetailView.as_view(), name="item-detail"),
]

wishlist_urlpatterns = [
    path("", WishlistView.as_view(), name="wishlist"),
    path("sync/", WishlistSyncView.as_view(), name="wishlist-sync"),
    path("<slug:slug>/", WishlistItemView.as_view(), name="wishlist-item"),
]
