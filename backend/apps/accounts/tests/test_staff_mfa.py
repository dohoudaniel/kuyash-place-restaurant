"""Two-factor authentication for the Django admin (SECURITY.md §8)."""

from __future__ import annotations

import re
import time

import pytest
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse

from apps.accounts import staff_mfa
from apps.accounts.mfa_adapter import KuyashMFAAdapter
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

ADMIN = reverse("admin:index")
SETUP = reverse("staff_mfa:setup")
VERIFY = reverse("staff_mfa:verify")


@pytest.fixture(autouse=True)
def mfa_on(settings):  # type: ignore[no-untyped-def]
    settings.STAFF_MFA_REQUIRED = True


@pytest.fixture
def staff(db) -> User:  # type: ignore[no-untyped-def]
    return User.objects.create_user(
        email="staff@example.com", password="x" * 16, full_name="Sam Staff", is_staff=True
    )


def current_code(secret: str) -> str:
    return format_hotp_value(hotp_value(secret, int(time.time()) // 30))


def enrol(client, user: User) -> tuple[str, list[str]]:  # type: ignore[no-untyped-def]
    client.force_login(user)
    page = client.get(SETUP)
    secret = page.context["secret"]
    response = client.post(SETUP, {"code": current_code(secret), "next": ADMIN})
    return secret, list(response.context["codes"])


# ──────────────────────────────────────────────────────────────────────────────
# Enrolment
# ──────────────────────────────────────────────────────────────────────────────


def test_staff_are_sent_to_enrol_before_any_admin_page(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    response = client.get(ADMIN)
    assert response.status_code == 302
    assert response["Location"].startswith(SETUP)
    assert "next=/admin/" in response["Location"]


def test_enrolment_shows_a_qr_code_and_key(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    page = client.get(SETUP)
    body = page.content.decode()
    assert page.status_code == 200
    assert "<svg" in body
    assert re.fullmatch(r"[A-Z2-7=]{32}", page.context["secret"])
    assert client.get(SETUP).context["secret"] == page.context["secret"]  # stable across reloads


def test_a_wrong_enrolment_code_is_refused(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    client.get(SETUP)
    response = client.post(SETUP, {"code": "000000"})
    assert (
        "isn&#x27;t right" in response.content.decode()
        or "isn't right" in response.content.decode()
    )
    assert not Authenticator.objects.exists()


def test_enrolment_stores_encrypted_secrets_and_shows_recovery_codes(client, staff) -> None:  # type: ignore[no-untyped-def]
    secret, codes = enrol(client, staff)
    assert len(codes) == 10
    totp = Authenticator.objects.get(user=staff, type="totp")
    assert totp.data["secret"] != secret  # not stored in the clear
    assert KuyashMFAAdapter().decrypt(totp.data["secret"]) == secret
    recovery = Authenticator.objects.get(user=staff, type="recovery_codes")
    assert "seed" in recovery.data
    assert client.get(ADMIN).status_code == 200  # verified for this session


def test_enrolled_staff_are_not_sent_back_to_setup(client, staff) -> None:  # type: ignore[no-untyped-def]
    enrol(client, staff)
    response = client.get(SETUP)
    assert response.status_code == 302 and response["Location"].startswith(VERIFY)


# ──────────────────────────────────────────────────────────────────────────────
# Signing in
# ──────────────────────────────────────────────────────────────────────────────


def test_a_new_session_must_verify(client, staff) -> None:  # type: ignore[no-untyped-def]
    secret, _ = enrol(client, staff)
    client.logout()
    client.force_login(staff)
    held = client.get(ADMIN)
    assert held["Location"].startswith(VERIFY)

    response = client.post(VERIFY, {"code": current_code(secret), "next": ADMIN})
    assert response.status_code == 302 and response["Location"] == ADMIN
    assert client.get(ADMIN).status_code == 200


def test_a_code_cannot_be_replayed(client, staff) -> None:  # type: ignore[no-untyped-def]
    secret, _ = enrol(client, staff)
    code = current_code(secret)
    client.logout()
    client.force_login(staff)
    assert client.post(VERIFY, {"code": code}).status_code == 302
    client.logout()
    client.force_login(staff)
    assert client.post(VERIFY, {"code": code}).status_code == 200  # refused the second time


def test_a_recovery_code_works_once(client, staff) -> None:  # type: ignore[no-untyped-def]
    _, codes = enrol(client, staff)
    client.logout()
    client.force_login(staff)
    assert client.post(VERIFY, {"code": codes[0]}).status_code == 302
    client.logout()
    client.force_login(staff)
    assert client.post(VERIFY, {"code": codes[0]}).status_code == 200


def test_repeated_failures_lock_the_account_for_a_while(client, staff) -> None:  # type: ignore[no-untyped-def]
    secret, _ = enrol(client, staff)
    client.logout()
    client.force_login(staff)
    for _ in range(staff_mfa.MAX_FAILURES):
        client.post(VERIFY, {"code": "000000"})
    locked = client.post(VERIFY, {"code": current_code(secret)})
    assert locked.status_code == 200
    assert "Too many attempts" in locked.content.decode()
    cache.clear()
    assert client.post(VERIFY, {"code": current_code(secret)}).status_code == 302


@pytest.mark.parametrize("target", ["https://evil.example/", "//evil.example/", "/api/v1/orders/"])
def test_next_cannot_leave_the_admin(client, staff, target) -> None:  # type: ignore[no-untyped-def]
    secret, _ = enrol(client, staff)
    client.logout()
    client.force_login(staff)
    cache.clear()  # forget the enrolment code so the same 30-second code is accepted
    response = client.post(VERIFY, {"code": current_code(secret), "next": target})
    assert response.status_code == 302 and response["Location"] == ADMIN


def test_verify_before_enrolment_goes_to_setup(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    assert client.get(VERIFY)["Location"].startswith(SETUP)


def test_already_verified_skips_the_form(client, staff) -> None:  # type: ignore[no-untyped-def]
    enrol(client, staff)
    response = client.get(VERIFY)
    assert response.status_code == 302 and response["Location"] == ADMIN


def test_the_verify_page_renders(client, staff) -> None:  # type: ignore[no-untyped-def]
    enrol(client, staff)
    client.logout()
    client.force_login(staff)
    page = client.get(VERIFY)
    assert page.status_code == 200 and "authenticator app" in page.content.decode()


def test_the_lockout_also_guards_enrolment(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    client.get(SETUP)
    for _ in range(staff_mfa.MAX_FAILURES):
        client.post(SETUP, {"code": "000000"})
    secret = client.get(SETUP).context["secret"]
    response = client.post(SETUP, {"code": current_code(secret)})
    assert "Too many attempts" in response.content.decode()


# ──────────────────────────────────────────────────────────────────────────────
# Who is affected
# ──────────────────────────────────────────────────────────────────────────────


def test_login_and_logout_are_never_held(client, staff) -> None:  # type: ignore[no-untyped-def]
    client.force_login(staff)
    assert client.get(reverse("admin:login")).status_code in (200, 302)
    assert not client.get(reverse("admin:login")).get("Location", "").startswith(SETUP)


def test_customers_are_not_affected(client, verified_user) -> None:  # type: ignore[no-untyped-def]
    client.force_login(verified_user)
    response = client.get(ADMIN)
    assert not response.get("Location", "").startswith(SETUP)  # the admin itself turns them away
    assert client.get(reverse("v1:auth:session")).status_code == 200


def test_the_two_factor_pages_need_a_staff_sign_in(client, verified_user) -> None:  # type: ignore[no-untyped-def]
    assert client.get(VERIFY)["Location"].startswith(reverse("admin:login"))
    client.force_login(verified_user)
    assert client.get(SETUP)["Location"].startswith(reverse("admin:login"))


def test_it_can_be_switched_off(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    settings.STAFF_MFA_REQUIRED = False
    client.force_login(staff)
    assert client.get(ADMIN).status_code == 200


def test_the_deploy_check_warns_when_it_is_off(settings) -> None:  # type: ignore[no-untyped-def]
    assert staff_mfa.check_staff_mfa_is_on(None) == []
    settings.STAFF_MFA_REQUIRED = False
    [warning] = staff_mfa.check_staff_mfa_is_on(None)
    assert warning.id == "kuyash.W020"


# ──────────────────────────────────────────────────────────────────────────────
# Reset
# ──────────────────────────────────────────────────────────────────────────────


def test_a_superuser_can_reset_a_lost_authenticator(client, staff) -> None:  # type: ignore[no-untyped-def]
    enrol(client, staff)
    root = User.objects.create_superuser(email="root@example.com", password="x" * 16)
    _, _root_codes = enrol(client, root)
    response = client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "reset_two_factor", "_selected_action": [str(staff.pk)]},
        follow=True,
    )
    assert "reset for 1 account" in response.content.decode()
    assert not Authenticator.objects.filter(user=staff).exists()


def test_only_superusers_can_reset(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    from django.contrib.auth.models import Permission

    enrol(client, staff)
    other = User.objects.create_user(
        email="other-staff@example.com", password="x" * 16, is_staff=True
    )
    staff.user_permissions.add(
        *Permission.objects.filter(codename__in=["view_user", "change_user"])
    )
    response = client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "reset_two_factor", "_selected_action": [str(other.pk)]},
        follow=True,
    )
    assert "Only a superuser" in response.content.decode()


def test_the_cli_can_reset_a_lost_authenticator(client, staff) -> None:  # type: ignore[no-untyped-def]
    """Break-glass. The admin action is superuser-only and sits *behind* the
    very gate it would unlock, so a sole superuser who loses their phone locks
    the whole admin — mid-service — with no way back in."""
    import io

    enrol(client, staff)
    assert Authenticator.objects.filter(user=staff).exists()

    out = io.StringIO()
    call_command("reset_staff_mfa", "staff@example.com", stdout=out)

    assert not Authenticator.objects.filter(user=staff).exists()
    assert "Cleared two-factor authentication" in out.getvalue()


def test_the_cli_normalises_the_email(client, staff) -> None:  # type: ignore[no-untyped-def]
    import io

    enrol(client, staff)
    call_command("reset_staff_mfa", "  STAFF@example.com ", stdout=io.StringIO())
    assert not Authenticator.objects.filter(user=staff).exists()


def test_the_cli_refuses_an_unknown_email() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="No account"):
        call_command("reset_staff_mfa", "nobody@example.com")


def test_the_cli_is_safe_to_run_twice(client, staff) -> None:  # type: ignore[no-untyped-def]
    import io

    enrol(client, staff)
    call_command("reset_staff_mfa", "staff@example.com", stdout=io.StringIO())

    out = io.StringIO()
    call_command("reset_staff_mfa", "staff@example.com", stdout=out)
    assert "nothing to reset" in out.getvalue()


def test_a_reset_staff_member_re_enrols_at_the_next_sign_in(client, staff) -> None:  # type: ignore[no-untyped-def]
    """It clears the enrolment rather than disabling the second factor."""
    import io

    enrol(client, staff)
    call_command("reset_staff_mfa", "staff@example.com", stdout=io.StringIO())

    client.logout()
    client.force_login(staff)
    assert client.get(ADMIN)["Location"].startswith(SETUP)


# ──────────────────────────────────────────────────────────────────────────────
# Elevation expiry
# ──────────────────────────────────────────────────────────────────────────────


def expire_elevation(client, seconds_ago: float) -> None:  # type: ignore[no-untyped-def]
    session = client.session
    session[staff_mfa.SESSION_VERIFIED_AT] = time.time() - seconds_ago
    session.save()


def test_elevation_expires_and_the_code_is_asked_for_again(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    """Sessions roll for 14 days, so a permanent elevation made the second
    factor a one-time gate rather than an ongoing control — a laptop left open
    on the pass stayed admin-authenticated for a fortnight."""
    settings.STAFF_MFA_ELEVATION_SECONDS = 8 * 60 * 60
    enrol(client, staff)
    assert client.get(ADMIN).status_code == 200

    expire_elevation(client, 8 * 60 * 60 + 60)

    held = client.get(ADMIN)
    assert held.status_code == 302
    assert held["Location"].startswith(VERIFY)


def test_a_recent_elevation_is_still_accepted(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    settings.STAFF_MFA_ELEVATION_SECONDS = 8 * 60 * 60
    enrol(client, staff)
    expire_elevation(client, 60)
    assert client.get(ADMIN).status_code == 200


def test_re_verifying_restores_access(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    settings.STAFF_MFA_ELEVATION_SECONDS = 8 * 60 * 60
    secret, _ = enrol(client, staff)
    expire_elevation(client, 8 * 60 * 60 + 60)
    cache.clear()  # forget the enrolment code so the current one is accepted

    assert client.post(VERIFY, {"code": current_code(secret), "next": ADMIN}).status_code == 302
    assert client.get(ADMIN).status_code == 200


def test_the_elevation_window_is_configurable(settings) -> None:  # type: ignore[no-untyped-def]
    settings.STAFF_MFA_ELEVATION_SECONDS = 900
    assert staff_mfa.elevation_max_age() == 900


def test_the_elevation_window_defaults_to_a_shift(settings) -> None:  # type: ignore[no-untyped-def]
    del settings.STAFF_MFA_ELEVATION_SECONDS
    assert staff_mfa.elevation_max_age() == staff_mfa.DEFAULT_ELEVATION_SECONDS == 8 * 60 * 60


def test_a_session_elevated_before_timestamps_existed_must_verify_again(client, staff) -> None:  # type: ignore[no-untyped-def]
    """Sessions already live at deploy time carry no timestamp."""
    enrol(client, staff)
    session = client.session
    del session[staff_mfa.SESSION_VERIFIED_AT]
    session.save()

    assert client.get(ADMIN)["Location"].startswith(VERIFY)


def test_a_tampered_timestamp_must_verify_again(client, staff) -> None:  # type: ignore[no-untyped-def]
    enrol(client, staff)
    session = client.session
    session[staff_mfa.SESSION_VERIFIED_AT] = "not-a-number"
    session.save()

    assert client.get(ADMIN)["Location"].startswith(VERIFY)


def test_the_recovery_codes_page_offers_a_download(client, staff) -> None:  # type: ignore[no-untyped-def]
    """Shown once, so "write these down quickly" was the only option."""
    client.force_login(staff)
    secret = client.get(SETUP).context["secret"]
    response = client.post(SETUP, {"code": current_code(secret), "next": ADMIN})

    body = response.content.decode()
    assert 'download="kuyash-recovery-codes.txt"' in body
    assert "data:text/plain" in body
    assert "reset_staff_mfa" in body  # the break-glass path is documented there


def test_rotating_the_secret_key_makes_old_secrets_unreadable(client, staff, settings) -> None:  # type: ignore[no-untyped-def]
    from cryptography.fernet import InvalidToken

    enrol(client, staff)
    stored = Authenticator.objects.get(user=staff, type="totp").data["secret"]
    settings.SECRET_KEY = "a-completely-different-key"
    with pytest.raises(InvalidToken):
        KuyashMFAAdapter().decrypt(stored)


def test_migrations_for_mfa_are_applied() -> None:
    call_command("migrate", "mfa", "--check", verbosity=0)
