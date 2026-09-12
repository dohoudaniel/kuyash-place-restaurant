"""Kitchen Display routes.

Separate from the customer API: different audience, different permissions,
different tempo.
"""

from __future__ import annotations

from django.urls import path

from apps.orders.views import (
    KDSAssignRiderView,
    KDSAvailabilityView,
    KDSQueueView,
    KDSSummaryView,
    KDSTransitionView,
)

app_name = "kds"

urlpatterns = [
    path("orders/", KDSQueueView.as_view(), name="queue"),
    path("summary/", KDSSummaryView.as_view(), name="summary"),
    # Specific routes first: Django matches in order, so a generic
    # <str:action> declared above would swallow "assign-rider".
    path("orders/<str:reference>/assign-rider/", KDSAssignRiderView.as_view(), name="assign-rider"),
    path(
        "orders/<str:reference>/<str:action>/",
        KDSTransitionView.as_view(),
        name="transition",
    ),
    path("items/<slug:slug>/availability/", KDSAvailabilityView.as_view(), name="availability"),
]
