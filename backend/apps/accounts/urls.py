"""Account and authentication routes."""

from __future__ import annotations

from django.urls import path

from apps.accounts.views import (
    AddressDetailView,
    AddressListCreateView,
    AddressSetDefaultView,
    CSRFView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
    ResendVerificationView,
    SessionView,
    VerifyEmailView,
)

auth_urlpatterns = [
    path("csrf/", CSRFView.as_view(), name="csrf"),
    path("session/", SessionView.as_view(), name="session"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
]

account_urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("addresses/", AddressListCreateView.as_view(), name="addresses"),
    path("addresses/<uuid:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<uuid:pk>/set-default/",
        AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
]
