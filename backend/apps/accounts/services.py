"""Account services.

All authentication business logic lives here so it can be tested without HTTP.
"""

from __future__ import annotations

import logging
import secrets

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.accounts.models import Profile, User
from apps.accounts.signals import email_verified, user_anonymised
from apps.notifications.services import queue_templated_email

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised for authentication failures that are safe to report to a caller."""

    def __init__(self, detail: str, code: str = "authentication_failed") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


# ──────────────────────────────────────────────────────────────────────────────
# Registration and verification
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    full_name: str = "",
    phone: str = "",
    marketing_opt_in: bool = False,
) -> User:
    """Create an account and send a verification email."""
    user = User.objects.create_user(
        email=email, password=password, full_name=full_name, phone=phone
    )
    profile, _ = Profile.objects.get_or_create(user=user)
    if marketing_opt_in:
        profile.marketing_opt_in = True
        profile.save(update_fields=["marketing_opt_in", "updated_at"])

    send_verification_email(user)
    return user


def send_verification_email(user: User) -> None:
    """Queue a verification email for a user's primary address."""
    address, _ = EmailAddress.objects.get_or_create(
        user=user, email=user.email, defaults={"primary": True, "verified": False}
    )
    if address.verified:
        return

    key = EmailConfirmationHMAC(address).key
    link = f"{settings.FRONTEND_URL}/verify-email?key={key}"
    queue_templated_email(
        template_key="verify_email",
        recipient=user.email,
        context={"name": user.get_short_name(), "link": link, "user_id": str(user.pk)},
    )


def _address_for_key(key: str) -> EmailAddress | None:
    """Resolve a confirmation key *without* allauth's ``verified=False`` filter.

    ``EmailConfirmationHMAC.from_key`` refuses a key whose address is already
    confirmed, and returns the same ``None`` it returns for a forged or expired
    one. That collapsed the ordinary second click — a second device, a mail
    client prefetching the link, a refresh — into "this link is invalid",
    followed by an offer to resend an email the API had already decided not to
    send. Reading the key again here is what lets the two cases be told apart.
    """
    from allauth.account import app_settings as allauth_settings

    max_age = 60 * 60 * 24 * allauth_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS
    try:
        pk = signing.loads(key, max_age=max_age, salt=allauth_settings.SALT)
    except signing.BadSignature:  # also covers SignatureExpired, which subclasses it
        return None
    return EmailAddress.objects.filter(pk=pk).first()


def verify_email(request: HttpRequest, key: str) -> User:
    """Confirm an email address from an emailed key."""
    confirmation = EmailConfirmationHMAC.from_key(key)
    if confirmation is None:
        address = _address_for_key(key)
        if address is not None and address.verified:
            raise AuthError(
                "That address is already confirmed — you can sign in.", "already_verified"
            )
        raise AuthError("That confirmation link is invalid or has expired.", "invalid_token")

    user = confirmation.email_address.user
    if not user.is_active:
        # Django's auth backend refuses to load an inactive user, so signing one
        # in produced an inert session rather than a real ban bypass. Refusing
        # explicitly beats depending on that happy accident.
        raise AuthError("This account has been deactivated.", "account_disabled")

    confirmation.confirm(request)
    user.refresh_from_db()
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])

    email_verified.send(sender=User, user=user)
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────


def authenticate_user(request: HttpRequest, *, email: str, password: str) -> User:
    """Authenticate, refusing unverified accounts.

    The error message is identical for "no such user" and "wrong password" so a
    caller cannot enumerate accounts by probing.
    """
    user = authenticate(request, username=email.lower().strip(), password=password)
    if user is None:
        raise AuthError("Email or password is incorrect.", "invalid_credentials")
    if not user.is_active:
        raise AuthError("This account has been deactivated.", "account_disabled")
    if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory" and not user.is_email_verified:
        raise AuthError(
            "Confirm your email address before signing in. We can send the link again.",
            "email_not_verified",
        )
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Passwords
# ──────────────────────────────────────────────────────────────────────────────


def request_password_reset(email: str) -> None:
    """Queue a reset email if the account exists.

    Returns ``None`` either way and never signals which case occurred (AS-3):
    a differing response is an account-enumeration oracle.
    """
    user = User.objects.filter(email=email.lower().strip(), is_active=True).first()
    if user is None:
        logger.info("password_reset_requested_for_unknown_email")
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    queue_templated_email(
        template_key="password_reset",
        recipient=user.email,
        context={"name": user.get_short_name(), "link": link, "user_id": str(user.pk)},
    )


@transaction.atomic
def confirm_password_reset(*, uid: str, token: str, new_password: str) -> User:
    """Complete a password reset and invalidate every existing session."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise AuthError("That reset link is invalid or has expired.", "invalid_token") from exc

    if not default_token_generator.check_token(user, token):
        raise AuthError("That reset link is invalid or has expired.", "invalid_token")

    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    _invalidate_sessions(user)
    return user


@transaction.atomic
def change_password(*, user: User, current_password: str, new_password: str) -> User:
    """Change a password, requiring the current one."""
    if not user.check_password(current_password):
        raise AuthError("Your current password is incorrect.", "invalid_credentials")
    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user


#: Session keys deleted per statement. Large enough that one statement covers
#: any realistic user, small enough not to build a multi-megabyte query.
_SESSION_DELETE_BATCH = 500


def _invalidate_sessions(user: User) -> None:
    """Drop every stored session belonging to a user (AS-1).

    **The ceiling on this function**, measured: Django's session table carries
    no user column, so finding one user's sessions means decoding every
    unexpired row — roughly 80µs each, so ~160ms at 2,000 live sessions. It runs
    on password reset *and* on account erasure, both of which are already slow
    paths, but it scales with total sessions rather than with this user's.

    What is fixed here is the part that could be: the deletes are batched into
    one statement instead of one per session (previously N round trips inside
    the reset transaction), and only the two columns needed are loaded rather
    than whole rows. Removing the decode entirely needs either a cache-backed
    session engine or a ``user → session`` index table — neither of which this
    function can introduce on its own, and both of which are settings/schema
    decisions rather than local ones.
    """
    from django.contrib.sessions.models import Session

    target = str(user.pk)
    doomed = [
        session.session_key
        for session in Session.objects.filter(expire_date__gte=timezone.now())
        .only("session_key", "session_data")
        .iterator(chunk_size=2000)
        if session.get_decoded().get("_auth_user_id") == target
    ]
    for start in range(0, len(doomed), _SESSION_DELETE_BATCH):
        Session.objects.filter(
            session_key__in=doomed[start : start + _SESSION_DELETE_BATCH]
        ).delete()


# ──────────────────────────────────────────────────────────────────────────────
# Erasure
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def anonymise_user(user: User) -> User:
    """Exercise the right to erasure (NDPR).

    The account is anonymised rather than deleted: financial records must be
    retained for seven years for tax, but they must not stay linked to a
    recognisable person. Other apps scrub their own data via ``user_anonymised``.
    """
    placeholder = f"deleted-{secrets.token_hex(8)}@removed.invalid"

    user.email = placeholder
    user.full_name = "Deleted account"
    user.phone = ""
    user.is_active = False
    user.is_email_verified = False
    user.set_unusable_password()
    user.save()

    Profile.objects.filter(user=user).update(date_of_birth=None, avatar="", marketing_opt_in=False)
    user.addresses.all().delete()
    EmailAddress.objects.filter(user=user).delete()
    _invalidate_sessions(user)

    user_anonymised.send(sender=User, user=user)
    return user


def validate_new_password(password: str, user: User | None = None) -> None:
    """Raise :class:`AuthError` if a password fails Django's validators."""
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise AuthError(" ".join(exc.messages), "weak_password") from exc


__all__ = [
    "AuthError",
    "anonymise_user",
    "authenticate_user",
    "change_password",
    "confirm_password_reset",
    "register_user",
    "request_password_reset",
    "send_verification_email",
    "validate_new_password",
    "verify_email",
]
