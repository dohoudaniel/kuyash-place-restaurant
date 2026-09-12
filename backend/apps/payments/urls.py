"""Payment routes."""

from __future__ import annotations

from django.urls import path

from apps.payments.methods_views import (
    PaymentMethodDefaultView,
    PaymentMethodDetailView,
    PaymentMethodListView,
)
from apps.payments.views import (
    FlutterwaveWebhookView,
    InitialisePaymentView,
    PaystackWebhookView,
    RefundView,
    VerifyPaymentView,
)

app_name = "payments"

urlpatterns = [
    path("initialise/", InitialisePaymentView.as_view(), name="initialise"),
    path("verify/<str:reference>/", VerifyPaymentView.as_view(), name="verify"),
    path("refund/<str:reference>/", RefundView.as_view(), name="refund"),
    path("methods/", PaymentMethodListView.as_view(), name="methods"),
    path("methods/<uuid:pk>/", PaymentMethodDetailView.as_view(), name="method-detail"),
    path(
        "methods/<uuid:pk>/set-default/",
        PaymentMethodDefaultView.as_view(),
        name="method-set-default",
    ),
]

webhook_urlpatterns = [
    path("paystack/", PaystackWebhookView.as_view(), name="paystack"),
    path("flutterwave/", FlutterwaveWebhookView.as_view(), name="flutterwave"),
]
