"""Two-factor authentication for the Django admin (SECURITY.md §8).

Customers sign in through the headless API; staff work in the Django admin,
which Django's own password form protects. This adds a second step there:

1. A staff member signs in to the admin with their password as usual.
2. Before any admin page loads, they must enter a 6-digit code from an
   authenticator app (or a one-time recovery code).
3. The first time, they enrol: scan a QR code, confirm a code, and are shown
   ten recovery codes once.

Authenticators are django-allauth's MFA models, encrypted at rest by
``KuyashMFAAdapter``. Verification is per session, so a staff member who signs
in through the public API still has to pass this step to reach the admin.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote

from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret, validate_totp_code
from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.core.checks import Warning, register
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

logger = logging.getLogger(__name__)

SESSION_VERIFIED = "kuyash.staff_mfa.user"
SESSION_VERIFIED_AT = "kuyash.staff_mfa.verified_at"
SESSION_PENDING_SECRET = "kuyash.staff_mfa.pending_secret"  # noqa: S105 - a session key name
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60

#: How long one verification lasts: a shift. Override with
#: ``STAFF_MFA_ELEVATION_SECONDS``.
DEFAULT_ELEVATION_SECONDS = 8 * 60 * 60


def admin_prefix() -> str:
    return "/" + settings.ADMIN_URL.lstrip("/")


def mfa_prefix() -> str:
    return admin_prefix() + "two-factor/"


def _is_staff(user: Any) -> bool:
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


def elevation_max_age() -> int:
    """How long an admin session stays elevated before the code is asked for again."""
    return int(getattr(settings, "STAFF_MFA_ELEVATION_SECONDS", DEFAULT_ELEVATION_SECONDS))


def is_verified(request: HttpRequest) -> bool:
    """Whether this session passed the second step, recently enough to still count.

    Sessions roll for 14 days, so treating an elevation as permanent made the
    second factor a one-time gate rather than an ongoing control: a laptop left
    open on the pass stayed admin-authenticated for a fortnight. The timestamp
    is what turns it back into a control.
    """
    if request.session.get(SESSION_VERIFIED) != str(request.user.pk):
        return False
    verified_at = request.session.get(SESSION_VERIFIED_AT)
    if not isinstance(verified_at, int | float):
        return False  # pre-timestamp session, or tampered: verify again
    return (time.time() - float(verified_at)) < elevation_max_age()


def totp_authenticator(user: Any) -> Authenticator | None:
    return Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).first()


class StaffMFAMiddleware:
    """Hold staff at the second step until they have passed it this session."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._must_verify(request):
            view = (
                "staff_mfa:setup"
                if totp_authenticator(request.user) is None
                else "staff_mfa:verify"
            )
            return HttpResponseRedirect(f"{reverse(view)}?next={quote(request.get_full_path())}")
        return self.get_response(request)

    @staticmethod
    def _must_verify(request: HttpRequest) -> bool:
        if not settings.STAFF_MFA_REQUIRED:
            return False
        path = request.path
        prefix = admin_prefix()
        if not path.startswith(prefix) or path.startswith(mfa_prefix()):
            return False
        if path in {prefix + "login/", prefix + "logout/"}:
            return False
        return _is_staff(request.user) and not is_verified(request)


def _staff_only(request: HttpRequest) -> HttpResponse | None:
    """The two-factor pages are for signed-in staff; everyone else goes to the admin login."""
    if not _is_staff(request.user):
        return HttpResponseRedirect(f"{reverse('admin:login')}?next={quote(admin_prefix())}")
    return None


def _next_url(request: HttpRequest) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    safe = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if safe and target.startswith(admin_prefix()) else reverse("admin:index")


def _mark_verified(request: HttpRequest) -> None:
    # A new session key at the moment of elevation, as at login.
    request.session.cycle_key()
    request.session[SESSION_VERIFIED] = str(request.user.pk)
    request.session[SESSION_VERIFIED_AT] = time.time()


def _context(request: HttpRequest, **extra: Any) -> dict[str, Any]:
    return {**admin.site.each_context(request), "next": _next_url(request), **extra}


def _locked(user: Any) -> bool:
    return (cache.get(f"staff-mfa-failures:{user.pk}") or 0) >= MAX_FAILURES


def _record_failure(user: Any) -> None:
    key = f"staff-mfa-failures:{user.pk}"
    failures = (cache.get(key) or 0) + 1
    cache.set(key, failures, LOCKOUT_SECONDS)
    logger.warning("staff_mfa_failed", extra={"user": str(user.pk), "failures": failures})


def verify(request: HttpRequest) -> HttpResponse:
    if (denied := _staff_only(request)) is not None:
        return denied
    authenticator = totp_authenticator(request.user)
    if authenticator is None:
        return redirect(f"{reverse('staff_mfa:setup')}?next={quote(_next_url(request))}")
    if is_verified(request):
        return HttpResponseRedirect(_next_url(request))

    error = ""
    if request.method == "POST":
        code = "".join(request.POST.get("code", "").split())
        if _locked(request.user):
            error = "Too many attempts. Wait 15 minutes, then try again."
        elif code and _check_code(request.user, authenticator, code):
            cache.delete(f"staff-mfa-failures:{request.user.pk}")
            _mark_verified(request)
            logger.info("staff_mfa_verified", extra={"user": str(request.user.pk)})
            return HttpResponseRedirect(_next_url(request))
        else:
            _record_failure(request.user)
            error = "That code isn't right. Codes change every 30 seconds — use the current one."
    return TemplateResponse(
        request,
        "admin/staff_mfa/verify.html",
        _context(request, title="Two-factor authentication", error=error),
    )


def _check_code(user: Any, authenticator: Authenticator, code: str) -> bool:
    if code.isdigit() and len(code) == 6 and TOTP(authenticator).validate_code(code):
        return True
    recovery = Authenticator.objects.filter(
        user=user, type=Authenticator.Type.RECOVERY_CODES
    ).first()
    if recovery is not None and RecoveryCodes(recovery).validate_code(code):
        logger.warning("staff_mfa_recovery_code_used", extra={"user": str(user.pk)})
        return True
    return False


def setup(request: HttpRequest) -> HttpResponse:
    if (denied := _staff_only(request)) is not None:
        return denied
    if totp_authenticator(request.user) is not None:
        return redirect(f"{reverse('staff_mfa:verify')}?next={quote(_next_url(request))}")

    secret = request.session.get(SESSION_PENDING_SECRET) or generate_totp_secret()
    request.session[SESSION_PENDING_SECRET] = secret
    error = ""
    if request.method == "POST":
        code = "".join(request.POST.get("code", "").split())
        if _locked(request.user):
            error = "Too many attempts. Wait 15 minutes, then try again."
        elif code.isdigit() and validate_totp_code(secret, code):
            TOTP.activate(request.user, secret)
            codes = RecoveryCodes.activate(request.user).get_unused_codes()
            request.session.pop(SESSION_PENDING_SECRET, None)
            cache.delete(f"staff-mfa-failures:{request.user.pk}")
            _mark_verified(request)
            logger.info("staff_mfa_enrolled", extra={"user": str(request.user.pk)})
            return TemplateResponse(
                request,
                "admin/staff_mfa/recovery_codes.html",
                _context(
                    request,
                    title="Save your recovery codes",
                    codes=codes,
                    # Backs the download link. Shown once, so "write these down
                    # quickly" was the only previous option.
                    codes_text="\n".join(codes),
                ),
            )
        else:
            _record_failure(request.user)
            error = "That code isn't right. Scan the QR code again and enter the current code."

    adapter = get_adapter()
    url = adapter.build_totp_url(request.user, secret)
    return TemplateResponse(
        request,
        "admin/staff_mfa/setup.html",
        _context(
            request,
            title="Set up two-factor authentication",
            secret=secret,
            qr_svg=adapter.build_totp_svg(url),
            error=error,
        ),
    )


def reset_for(user: Any) -> int:
    """Remove a staff member's authenticators (a lost phone). They re-enrol at next sign-in."""
    deleted, _ = Authenticator.objects.filter(user=user).delete()
    return deleted


@register("kuyash", deploy=True)
def check_staff_mfa_is_on(app_configs: Any, **kwargs: Any) -> list[Any]:
    if settings.STAFF_MFA_REQUIRED:
        return []
    return [
        Warning(
            "Two-factor authentication for the admin is switched off.",
            hint=(
                "Set STAFF_MFA_REQUIRED=true. Admin accounts can refund money "
                "and read customer data."
            ),
            id="kuyash.W020",
        )
    ]
