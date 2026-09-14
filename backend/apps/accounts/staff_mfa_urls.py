"""Admin two-factor routes, mounted under the admin prefix."""

from __future__ import annotations

from django.urls import path

from apps.accounts import staff_mfa

app_name = "staff_mfa"

urlpatterns = [
    path("verify/", staff_mfa.verify, name="verify"),
    path("setup/", staff_mfa.setup, name="setup"),
]
