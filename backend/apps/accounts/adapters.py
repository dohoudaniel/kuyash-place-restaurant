"""allauth adapters."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse

from apps.accounts.signals import email_verified

logger = logging.getLogger(__name__)


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


class KuyashSocialAdapter(DefaultSocialAccountAdapter):
    """Adapter for Google and Facebook sign-in.

    Two things matter here:

    * a social account must not become a way to take over an existing account
      by asserting an email the provider has not verified;
    * a customer who signs in with Google should end up with the same profile
      they would have had signing up with a password.
    """

    def is_auto_signup_allowed(self, request: HttpRequest, sociallogin: Any) -> bool:
        """Only create an account automatically when we have an email.

        Without one there is nothing to send an order confirmation to, and
        nothing to reconcile a later password signup against.
        """
        return bool(sociallogin.user.email) and super().is_auto_signup_allowed(request, sociallogin)

    def pre_social_login(self, request: HttpRequest, sociallogin: Any) -> None:
        """Refuse to link an unverified provider email to an existing account.

        allauth's own email-authentication setting handles the verified case.
        This is the backstop for a provider that claims an address it has not
        checked: linking on that basis would let anyone who can create an
        account at that provider take over a Kuyash account.
        """
        super().pre_social_login(request, sociallogin)

        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").lower().strip()
        if not email:
            return

        from apps.accounts.models import User

        existing = User.objects.filter(email=email).first()
        if existing is None:
            return

        verified_by_provider = any(
            (address.email or "").lower() == email and address.verified
            for address in sociallogin.email_addresses
        )
        if verified_by_provider:
            return  # allauth will connect it

        logger.warning(
            "social_login_unverified_email_collision",
            extra={"provider": sociallogin.account.provider},
        )

        # Browser sign-in arrives here on the provider's callback URL, on the API's
        # own origin. Answering with JSON would strand the customer on a raw error
        # document there, so send them back to the frontend with an error code it
        # can explain. Token-based flows (an app posting a provider token) have no
        # browser to redirect, and keep the JSON problem document.
        callback = self._frontend_callback(request, sociallogin)
        if callback:
            raise ImmediateHttpResponse(
                HttpResponseRedirect(
                    _with_query(
                        callback,
                        error="social_email_unverified",
                        error_process=sociallogin.state.get("process") or "login",
                    )
                )
            )

        raise ImmediateHttpResponse(
            JsonResponse(
                {
                    "type": "https://api.kuyashplace.com/errors/email-not-verified",
                    "title": "That email already has an account",
                    "status": 409,
                    "code": "social_email_unverified",
                    "detail": (
                        "An account already uses this email address. Sign in with your "
                        "password, or use a provider that has verified the address."
                    ),
                },
                status=409,
            )
        )

    @staticmethod
    def _frontend_callback(request: HttpRequest, sociallogin: Any) -> str:
        """The frontend URL a browser sign-in should return to, if there is one.

        allauth keeps the `callback_url` the frontend posted in the login state.
        It was validated when the flow started; it is checked again here because
        this value decides where a browser is sent.
        """
        from allauth.account.adapter import get_adapter as get_account_adapter

        state = getattr(sociallogin, "state", None) or {}
        target = state.get("next") or ""
        if not target:
            return ""
        return target if get_account_adapter(request).is_safe_url(target) else ""

    def save_user(self, request: HttpRequest, sociallogin: Any, form: Any = None) -> Any:
        """Give a social signup the same shape as a password signup."""
        user = super().save_user(request, sociallogin, form)

        data = sociallogin.account.extra_data or {}
        full_name = (data.get("name") or "").strip()
        if not user.full_name and full_name:
            user.full_name = full_name[:150]
            user.save(update_fields=["full_name", "updated_at"])

        # The provider vouched for the address, so there is nothing to confirm.
        if not user.is_email_verified and any(
            address.verified for address in sociallogin.email_addresses
        ):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
            email_verified.send(sender=type(user), user=user)

        return user


def _with_query(url: str, **params: str) -> str:
    """Append query parameters, keeping any the URL already has (e.g. ``next``)."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in params]
    query.extend(params.items())
    return urlunsplit(parts._replace(query=urlencode(query)))
