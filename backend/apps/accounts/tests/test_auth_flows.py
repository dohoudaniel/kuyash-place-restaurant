"""Registration, verification, login and password flows.

These replace the frontend's `setTimeout(() => alert("Login successful!"), 1000)`.
"""

from __future__ import annotations

import re

import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus

pytestmark = pytest.mark.django_db


def register_payload(**overrides: object) -> dict[str, object]:
    return {
        "email": "ada@example.com",
        "password": "correct-horse-battery-staple",
        "full_name": "Ada Obi",
        "phone": "+2348012345678",
        "accept_terms": True,
        **overrides,
    }


def verification_key() -> str:
    body = Notification.objects.get(template_key="verify_email").body
    match = re.search(r"verify-email\?key=([^\s]+)", body)
    assert match, f"no verification link in email body: {body}"
    return match.group(1)


# ── Registration ──────────────────────────────────────────────────────────────


def test_registration_creates_an_unverified_user(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(reverse("v1:auth:register"), register_payload(), format="json")
    assert response.status_code == 201
    assert response.json()["email_verification_required"] is True

    user = User.objects.get(email="ada@example.com")
    assert user.is_email_verified is False
    assert user.full_name == "Ada Obi"


def test_registration_queues_and_records_a_verification_email(api_client) -> None:  # type: ignore[no-untyped-def]
    api_client.post(reverse("v1:auth:register"), register_payload(), format="json")
    notification = Notification.objects.get(template_key="verify_email")
    assert notification.recipient == "ada@example.com"
    assert notification.status == NotificationStatus.SENT


def test_registration_requires_accepting_the_terms(api_client) -> None:  # type: ignore[no-untyped-def]
    """Server-side. The UI enforces this with an alert(), which is bypassable."""
    response = api_client.post(
        reverse("v1:auth:register"), register_payload(accept_terms=False), format="json"
    )
    assert response.status_code == 400
    assert "accept_terms" in response.json()["errors"]
    assert not User.objects.exists()


def test_registration_rejects_a_weak_password(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:auth:register"), register_payload(password="password123"), format="json"
    )
    assert response.status_code == 400
    assert not User.objects.exists()


def test_registration_rejects_a_duplicate_email(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(reverse("v1:auth:register"), register_payload(), format="json")
    assert response.status_code == 400
    assert "email" in response.json()["errors"]


def test_registration_records_marketing_consent(api_client) -> None:  # type: ignore[no-untyped-def]
    api_client.post(
        reverse("v1:auth:register"), register_payload(marketing_opt_in=True), format="json"
    )
    assert User.objects.get(email="ada@example.com").profile.marketing_opt_in is True


def test_marketing_consent_defaults_to_off(api_client) -> None:  # type: ignore[no-untyped-def]
    """NDPR: consent is opt-in, never assumed."""
    api_client.post(reverse("v1:auth:register"), register_payload(), format="json")
    assert User.objects.get(email="ada@example.com").profile.marketing_opt_in is False


# ── Verification ──────────────────────────────────────────────────────────────


def test_verification_confirms_the_address_and_signs_in(api_client) -> None:  # type: ignore[no-untyped-def]
    api_client.post(reverse("v1:auth:register"), register_payload(), format="json")
    response = api_client.post(
        reverse("v1:auth:verify-email"), {"key": verification_key()}, format="json"
    )
    assert response.status_code == 200

    user = User.objects.get(email="ada@example.com")
    assert user.is_email_verified is True
    assert EmailAddress.objects.get(user=user).verified is True

    session = api_client.get(reverse("v1:auth:session")).json()
    assert session["user"]["email"] == "ada@example.com"


def test_a_bogus_verification_key_is_rejected(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:auth:verify-email"), {"key": "not-a-real-key"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"


def test_resend_verification_does_not_reveal_account_existence(api_client) -> None:  # type: ignore[no-untyped-def]
    known = api_client.post(
        reverse("v1:auth:resend-verification"), {"email": "ada@example.com"}, format="json"
    )
    unknown = api_client.post(
        reverse("v1:auth:resend-verification"), {"email": "nobody@example.com"}, format="json"
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_establishes_a_session(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:auth:login"),
        {"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "ada@example.com"
    assert api_client.get(reverse("v1:auth:session")).json()["user"] is not None


def test_login_is_rejected_before_verification(api_client) -> None:  # type: ignore[no-untyped-def]
    User.objects.create_user(email="ada@example.com", password="correct-horse-battery-staple")
    response = api_client.post(
        reverse("v1:auth:login"),
        {"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"


def test_wrong_password_and_unknown_account_are_indistinguishable(  # type: ignore[no-untyped-def]
    api_client, verified_user: User
) -> None:
    """Differing responses would be an account-enumeration oracle."""
    wrong = api_client.post(
        reverse("v1:auth:login"),
        {"email": "ada@example.com", "password": "wrong-password-entirely"},
        format="json",
    )
    unknown = api_client.post(
        reverse("v1:auth:login"),
        {"email": "nobody@example.com", "password": "wrong-password-entirely"},
        format="json",
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_deactivated_account_cannot_sign_in(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    verified_user.is_active = False
    verified_user.save()
    response = api_client.post(
        reverse("v1:auth:login"),
        {"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert response.status_code == 401


def test_logout_clears_the_session(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    assert api_client.post(reverse("v1:auth:logout")).status_code == 204
    api_client.force_authenticate(user=None)
    assert api_client.get(reverse("v1:auth:session")).json()["user"] is None


# ── Passwords ─────────────────────────────────────────────────────────────────


def test_password_reset_response_is_identical_for_unknown_emails(api_client, verified_user) -> None:  # type: ignore[no-untyped-def]
    known = api_client.post(
        reverse("v1:auth:password-reset"), {"email": "ada@example.com"}, format="json"
    )
    unknown = api_client.post(
        reverse("v1:auth:password-reset"), {"email": "nobody@example.com"}, format="json"
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert Notification.objects.filter(template_key="password_reset").count() == 1


def test_password_reset_round_trip(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.post(reverse("v1:auth:password-reset"), {"email": "ada@example.com"}, format="json")
    body = Notification.objects.get(template_key="password_reset").body
    match = re.search(r"uid=([^&]+)&token=([^\s]+)", body)
    assert match
    uid, token = match.groups()

    response = api_client.post(
        reverse("v1:auth:password-reset-confirm"),
        {"uid": uid, "token": token, "new_password": "a-brand-new-long-passphrase"},
        format="json",
    )
    assert response.status_code == 200

    verified_user.refresh_from_db()
    assert verified_user.check_password("a-brand-new-long-passphrase")


def test_a_reset_token_cannot_be_reused(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.post(reverse("v1:auth:password-reset"), {"email": "ada@example.com"}, format="json")
    body = Notification.objects.get(template_key="password_reset").body
    uid, token = re.search(r"uid=([^&]+)&token=([^\s]+)", body).groups()  # type: ignore[union-attr]

    payload = {"uid": uid, "token": token, "new_password": "a-brand-new-long-passphrase"}
    assert (
        api_client.post(
            reverse("v1:auth:password-reset-confirm"), payload, format="json"
        ).status_code
        == 200
    )
    second = api_client.post(
        reverse("v1:auth:password-reset-confirm"),
        {**payload, "new_password": "yet-another-long-passphrase"},
        format="json",
    )
    assert second.status_code == 400
    assert second.json()["code"] == "invalid_token"


def test_reset_rejects_a_forged_token(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    response = api_client.post(
        reverse("v1:auth:password-reset-confirm"),
        {
            "uid": urlsafe_base64_encode(force_bytes(verified_user.pk)),
            "token": "made-up-token",
            "new_password": "a-brand-new-long-passphrase",
        },
        format="json",
    )
    assert response.status_code == 400


def test_password_change_requires_the_current_password(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:auth:password-change"),
        {"current_password": "not-the-right-one", "new_password": "a-brand-new-long-passphrase"},
        format="json",
    )
    assert response.status_code == 401
    verified_user.refresh_from_db()
    assert verified_user.check_password("correct-horse-battery-staple")


def test_password_change_succeeds_with_the_current_password(
    api_client, verified_user: User
) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:auth:password-change"),
        {
            "current_password": "correct-horse-battery-staple",
            "new_password": "a-brand-new-long-passphrase",
        },
        format="json",
    )
    assert response.status_code == 200
    verified_user.refresh_from_db()
    assert verified_user.check_password("a-brand-new-long-passphrase")


def test_password_change_requires_authentication(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:auth:password-change"),
        {"current_password": "x", "new_password": "y"},
        format="json",
    )
    assert response.status_code in (401, 403)
