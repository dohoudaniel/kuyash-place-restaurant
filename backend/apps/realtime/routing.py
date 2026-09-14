"""WebSocket routes."""

from __future__ import annotations

from django.urls import path

from apps.realtime.consumers import KitchenConsumer, OrderConsumer

websocket_urlpatterns = [
    path("ws/orders/<str:reference>/", OrderConsumer.as_asgi()),
    path("ws/kds/", KitchenConsumer.as_asgi()),
]
