"""allauth adapters."""

from __future__ import annotations

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest


class KuyashAccountAdapter(DefaultAccountAdapter):
    """Captures the extra fields the signup form collects.

    The frontend's signup form asks for full name, phone, terms acceptance and a
    newsletter opt-in. Terms acceptance is validated server-side in Phase 1B —
    the current UI enforces it with an ``alert()``, which is trivially bypassed
    and legally worthless.
    """

    def save_user(
        self,
        request: HttpRequest,
        user: Any,
        form: Any,
        commit: bool = True,
    ) -> Any:
        user = super().save_user(request, user, form, commit=False)
        data = getattr(form, "cleaned_data", {}) or {}
        if data.get("full_name"):
            user.full_name = data["full_name"]
        if data.get("phone"):
            user.phone = data["phone"]
        if commit:
            user.save()
            if data.get("marketing_opt_in") is not None:
                profile = getattr(user, "profile", None)
                if profile is not None:
                    profile.marketing_opt_in = bool(data["marketing_opt_in"])
                    profile.save(update_fields=["marketing_opt_in", "updated_at"])
        return user

    def add_message(self, *args: Any, **kwargs: Any) -> None:
        """Suppress Django messages.

        This is a headless, JSON-only API (``HEADLESS_ONLY``). Nothing renders a
        message framework flash, so queueing them only grows the session and
        makes the adapter depend on MessageMiddleware being present on every
        code path that touches it.
        """
        return None

    def confirm_email(self, request: HttpRequest, email_address: Any) -> None:
        """Mark verification on our own flag too, and claim any guest orders.

        Guest-order claiming lands in Phase 1B; the hook exists here so the
        behaviour has an obvious home rather than being bolted on later.
        """
        super().confirm_email(request, email_address)
        user = email_address.user
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
