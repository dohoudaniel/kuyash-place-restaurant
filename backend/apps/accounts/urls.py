"""Account routes.

Registration, login, password reset and email verification are served by
allauth headless under ``/_allauth/``. Phase 1B adds thin wrappers here that
match the paths in ``docs/API_SPEC.md`` §3.
"""

from __future__ import annotations

from django.urls import path

from apps.accounts.views import CSRFView, SessionView

app_name = "accounts"

urlpatterns = [
    path("csrf/", CSRFView.as_view(), name="csrf"),
    path("session/", SessionView.as_view(), name="session"),
]
