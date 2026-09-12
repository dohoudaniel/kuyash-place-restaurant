"""Profile and address-book endpoints.

These replace `ProfileSection.tsx`'s hardcoded "John Doe" and the two fixed
Lagos addresses every visitor currently sees.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import Address, User
from apps.delivery.models import DeliveryZone

pytestmark = pytest.mark.django_db


def address_payload(**overrides: object) -> dict[str, object]:
    return {
        "label": "home",
        "recipient_name": "Ada Obi",
        "phone": "+2348012345678",
        "street": "12 Adeola Odeku Street",
        "area": "Victoria Island",
        "city": "Lagos",
        "state": "Lagos",
        "landmark": "Opposite Eko Hotel",
        **overrides,
    }


# ── Profile ───────────────────────────────────────────────────────────────────


def test_profile_returns_the_real_user(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:accounts:me")).json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Obi"
    assert body["is_email_verified"] is True


def test_profile_requires_authentication(api_client) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:accounts:me")).status_code in (401, 403)


def test_profile_update_persists(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.patch(
        reverse("v1:accounts:me"),
        {"full_name": "Adaeze Obi", "date_of_birth": "1995-04-12"},
        format="json",
    )
    assert response.status_code == 200

    verified_user.refresh_from_db()
    assert verified_user.full_name == "Adaeze Obi"
    assert str(verified_user.profile.date_of_birth) == "1995-04-12"


def test_email_cannot_be_changed_through_the_profile(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    """AS-5: changing an email must re-verify it. Until that flow exists, the
    safe behaviour is to refuse the change rather than allow an unverified one."""
    api_client.force_authenticate(user=verified_user)
    api_client.patch(reverse("v1:accounts:me"), {"email": "attacker@evil.test"}, format="json")

    verified_user.refresh_from_db()
    assert verified_user.email == "ada@example.com"


def test_verification_status_cannot_be_self_granted(api_client) -> None:  # type: ignore[no-untyped-def]
    user = User.objects.create_user(
        email="ada@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=user)
    api_client.patch(reverse("v1:accounts:me"), {"is_email_verified": True}, format="json")

    user.refresh_from_db()
    assert user.is_email_verified is False


# ── Erasure (NDPR) ────────────────────────────────────────────────────────────


def test_account_erasure_anonymises_rather_than_deletes(api_client, verified_user: User) -> None:  # type: ignore[no-untyped-def]
    """Financial records must survive for tax; the person must not be identifiable."""
    Address.objects.create(user=verified_user, **address_payload())
    api_client.force_authenticate(user=verified_user)

    assert api_client.delete(reverse("v1:accounts:me")).status_code == 204

    verified_user.refresh_from_db()
    assert User.objects.filter(pk=verified_user.pk).exists()  # row retained
    assert verified_user.email.endswith("@removed.invalid")
    assert verified_user.full_name == "Deleted account"
    assert verified_user.phone == ""
    assert verified_user.is_active is False
    assert verified_user.has_usable_password() is False
    assert verified_user.addresses.count() == 0


# ── Addresses ─────────────────────────────────────────────────────────────────


def test_creating_an_address_resolves_its_zone(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(reverse("v1:accounts:addresses"), address_payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["zone"]["name"] == "Victoria Island"
    assert body["zone"]["fee"]["display"] == "₦1,500.00"
    assert body["is_deliverable"] is True


def test_an_address_outside_the_delivery_area_has_no_zone(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    """`zone: null` must be distinguishable, so the UI can offer pickup instead
    of letting the customer discover the problem at checkout."""
    api_client.force_authenticate(user=verified_user)
    body = api_client.post(
        reverse("v1:accounts:addresses"),
        address_payload(area="Wuse II", city="Abuja", state="FCT"),
        format="json",
    ).json()
    assert body["zone"] is None
    assert body["is_deliverable"] is False


def test_the_first_address_becomes_the_default(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    api_client.force_authenticate(user=verified_user)
    body = api_client.post(
        reverse("v1:accounts:addresses"), address_payload(), format="json"
    ).json()
    assert body["is_default"] is True


def test_only_one_address_is_ever_default(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    api_client.force_authenticate(user=verified_user)
    api_client.post(reverse("v1:accounts:addresses"), address_payload(), format="json")
    second = api_client.post(
        reverse("v1:accounts:addresses"),
        address_payload(label="work", street="45 Business Avenue", is_default=True),
        format="json",
    ).json()

    assert second["is_default"] is True
    assert Address.objects.filter(user=verified_user, is_default=True).count() == 1


def test_set_default_endpoint_promotes_an_address(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    api_client.force_authenticate(user=verified_user)
    first = Address.objects.create(user=verified_user, is_default=True, **address_payload())
    second = Address.objects.create(
        user=verified_user, **address_payload(label="work", street="45 Business Avenue")
    )

    response = api_client.post(reverse("v1:accounts:address-set-default", kwargs={"pk": second.pk}))
    assert response.status_code == 200

    first.refresh_from_db()
    second.refresh_from_db()
    assert second.is_default is True
    assert first.is_default is False


def test_deleting_the_default_promotes_another(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    """A customer with addresses should never be left with no default."""
    api_client.force_authenticate(user=verified_user)
    default = Address.objects.create(user=verified_user, is_default=True, **address_payload())
    other = Address.objects.create(
        user=verified_user, **address_payload(label="work", street="45 Business Avenue")
    )

    api_client.delete(reverse("v1:accounts:address-detail", kwargs={"pk": default.pk}))

    other.refresh_from_db()
    assert other.is_default is True


def test_a_user_cannot_read_another_users_address(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    """Today /account is a public route showing the same fabricated person to everyone."""
    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    address = Address.objects.create(user=verified_user, **address_payload())

    api_client.force_authenticate(user=intruder)
    url = reverse("v1:accounts:address-detail", kwargs={"pk": address.pk})
    assert api_client.get(url).status_code == 404
    assert api_client.delete(url).status_code == 404


def test_address_list_is_scoped_to_the_caller(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone
) -> None:
    other = User.objects.create_user(
        email="other@example.com", password="correct-horse-battery-staple"
    )
    Address.objects.create(user=other, **address_payload(recipient_name="Someone Else"))
    Address.objects.create(user=verified_user, **address_payload())

    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:accounts:addresses")).json()
    assert len(body) == 1
    assert body[0]["recipient_name"] == "Ada Obi"


def test_zone_is_recomputed_when_the_address_moves(  # type: ignore[no-untyped-def]
    api_client, verified_user: User, zone: DeliveryZone, branch
) -> None:
    lekki = DeliveryZone.objects.create(
        branch=branch,
        name="Lekki Phase 1",
        slug="lekki-phase-1",
        fee=250_000,
        min_order_value=300_000,
        areas=["Lekki"],
        display_order=2,
    )
    address = Address.objects.create(user=verified_user, **address_payload())
    assert address.zone == zone

    address.area = "Lekki"
    address.save()
    assert address.zone == lekki


def test_a_hand_picked_zone_is_not_overwritten(  # type: ignore[no-untyped-def]
    verified_user: User, zone: DeliveryZone, branch
) -> None:
    """Staff correcting a bad match must not have the correction undone on save."""
    lekki = DeliveryZone.objects.create(
        branch=branch,
        name="Lekki Phase 1",
        slug="lekki-phase-1",
        fee=250_000,
        min_order_value=300_000,
        areas=["Lekki"],
    )
    address = Address.objects.create(user=verified_user, **address_payload())
    address.zone = lekki
    address.zone_overridden = True
    address.save()

    address.refresh_from_db()
    assert address.zone == lekki  # not re-resolved back to Victoria Island
