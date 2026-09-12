"""Saved payment methods.

Replaces `PaymentMethodsSection.tsx`, which hardcodes a Visa •4242 and a
Mastercard •5555 and shows the same two to every visitor.

The governing rule: what is stored is a provider token, never a card.
"""

from __future__ import annotations

import pytest
import responses
from django.urls import reverse
from django.utils import timezone

from apps.payments.models import PaymentTransaction, SavedPaymentMethod, TransactionStatus
from apps.payments.services.payments import verify_and_settle

pytestmark = pytest.mark.django_db

VERIFY_URL = "https://api.paystack.co/transaction/verify/"


def mock_verify(reference: str, amount: int, *, auth_code: str = "AUTH_abc123") -> None:
    responses.add(
        responses.GET,
        f"{VERIFY_URL}{reference}",
        json={
            "status": True,
            "data": {
                "status": "success",
                "amount": amount,
                "currency": "NGN",
                "channel": "card",
                "authorization": {
                    "authorization_code": auth_code,
                    "last4": "4242",
                    "brand": "visa",
                    "exp_month": "12",
                    "exp_year": "2029",
                },
            },
        },
        status=200,
    )


# ── Consent ───────────────────────────────────────────────────────────────────


@responses.activate
def test_a_card_is_not_saved_without_consent(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """A provider returns a reusable token either way. Storing one nobody asked
    for would be collecting a payment credential without consent."""
    assert transaction.save_method is False
    mock_verify(transaction.our_reference, transaction.amount)

    verify_and_settle(transaction)

    assert SavedPaymentMethod.objects.count() == 0


@responses.activate
def test_a_card_is_saved_when_asked(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    PaymentTransaction.objects.filter(pk=transaction.pk).update(save_method=True)
    transaction.refresh_from_db()
    mock_verify(transaction.our_reference, transaction.amount)

    verify_and_settle(transaction)

    method = SavedPaymentMethod.objects.get()
    assert method.user == transaction.order.user
    assert method.authorization_code == "AUTH_abc123"
    assert method.card_last4 == "4242"
    assert method.card_brand == "visa"
    assert method.is_default is True  # the first one saved
    assert method.last_used_at is not None


@responses.activate
def test_no_token_means_nothing_to_save(transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """Bank transfer and USSD settle without a reusable authorization code."""
    PaymentTransaction.objects.filter(pk=transaction.pk).update(save_method=True)
    transaction.refresh_from_db()
    mock_verify(transaction.our_reference, transaction.amount, auth_code="")

    verify_and_settle(transaction)

    assert SavedPaymentMethod.objects.count() == 0


@responses.activate
def test_a_guest_order_saves_nothing(ready_cart, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """There is no account to attach the token to."""
    from apps.carts.models import FulfilmentType
    from apps.orders.services.placement import place_order

    ready_cart.user = None
    ready_cart.fulfilment_type = FulfilmentType.PICKUP
    ready_cart.delivery_address = None
    ready_cart.save()

    order = place_order(
        cart=ready_cart,
        payment_method="card",
        guest={"email": "guest@example.com", "phone": "+2348012345678"},
    )
    record = PaymentTransaction.objects.create(
        order=order,
        provider="paystack",
        our_reference=f"{order.reference}-g",
        provider_reference=f"{order.reference}-g",
        amount=order.grand_total,
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
        save_method=True,
    )
    mock_verify(record.our_reference, record.amount)

    verify_and_settle(record)
    assert SavedPaymentMethod.objects.count() == 0


@responses.activate
def test_reusing_the_same_card_updates_rather_than_duplicates(  # type: ignore[no-untyped-def]
    transaction, paystack_keys, ready_cart
) -> None:
    PaymentTransaction.objects.filter(pk=transaction.pk).update(save_method=True)
    transaction.refresh_from_db()
    mock_verify(transaction.our_reference, transaction.amount)
    verify_and_settle(transaction)
    first_used = SavedPaymentMethod.objects.get().last_used_at

    second = PaymentTransaction.objects.create(
        order=transaction.order,
        provider="paystack",
        our_reference=f"{transaction.order.reference}-2",
        provider_reference=f"{transaction.order.reference}-2",
        amount=transaction.amount,
        status=TransactionStatus.PENDING,
        initialised_at=timezone.now(),
        save_method=True,
    )
    mock_verify(second.our_reference, second.amount)
    verify_and_settle(second)

    assert SavedPaymentMethod.objects.count() == 1
    assert SavedPaymentMethod.objects.get().last_used_at >= first_used


# ── No card data, ever ────────────────────────────────────────────────────────


def test_the_model_cannot_hold_a_card_number() -> None:
    names = {field.name.lower() for field in SavedPaymentMethod._meta.fields}
    assert not names & {"card_number", "pan", "cvv", "cvc", "security_code"}
    assert "authorization_code" in names


def test_the_api_exposes_no_card_number(api_client, verified_user, db) -> None:  # type: ignore[no-untyped-def]
    SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_x",
        card_last4="4242",
        card_brand="visa",
        card_exp_month="12",
        card_exp_year="2029",
    )
    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:payments:methods")).json()

    assert body[0]["card_label"] == "visa ending 4242"
    assert "authorization_code" not in body[0]
    assert not set(body[0]) & {"card_number", "cvv", "pan"}


# ── Managing saved cards ──────────────────────────────────────────────────────


@pytest.fixture
def two_cards(db, verified_user):  # type: ignore[no-untyped-def]
    first = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_1",
        card_last4="4242",
        card_brand="visa",
        is_default=True,
    )
    second = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_2",
        card_last4="5555",
        card_brand="mastercard",
    )
    return first, second


def test_listing_is_scoped_to_the_caller(api_client, verified_user, two_cards, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    other = User.objects.create_user(
        email="other@example.com", password="correct-horse-battery-staple"
    )
    SavedPaymentMethod.objects.create(
        user=other, provider="paystack", authorization_code="AUTH_other", card_last4="9999"
    )

    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:payments:methods")).json()
    assert {row["card_last4"] for row in body} == {"4242", "5555"}


def test_forgetting_a_card_deactivates_rather_than_deletes(  # type: ignore[no-untyped-def]
    api_client, verified_user, two_cards
) -> None:
    """A hard delete would orphan the token's trail on historical transactions."""
    first, second = two_cards
    api_client.force_authenticate(user=verified_user)

    response = api_client.delete(reverse("v1:payments:method-detail", kwargs={"pk": first.pk}))
    assert response.status_code == 200

    first.refresh_from_db()
    assert first.is_active is False
    assert SavedPaymentMethod.objects.filter(pk=first.pk).exists()
    assert [row["card_last4"] for row in response.json()] == ["5555"]


def test_forgetting_the_default_promotes_another(api_client, verified_user, two_cards) -> None:  # type: ignore[no-untyped-def]
    first, second = two_cards
    api_client.force_authenticate(user=verified_user)
    api_client.delete(reverse("v1:payments:method-detail", kwargs={"pk": first.pk}))

    second.refresh_from_db()
    assert second.is_default is True


def test_setting_a_different_default(api_client, verified_user, two_cards) -> None:  # type: ignore[no-untyped-def]
    first, second = two_cards
    api_client.force_authenticate(user=verified_user)

    response = api_client.post(reverse("v1:payments:method-set-default", kwargs={"pk": second.pk}))
    assert response.status_code == 200

    first.refresh_from_db()
    second.refresh_from_db()
    assert second.is_default is True
    assert first.is_default is False


def test_another_user_cannot_touch_a_saved_card(api_client, verified_user, two_cards, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    first, _ = two_cards
    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=intruder)

    assert (
        api_client.delete(reverse("v1:payments:method-detail", kwargs={"pk": first.pk})).status_code
        == 404
    )
    assert (
        api_client.post(
            reverse("v1:payments:method-set-default", kwargs={"pk": first.pk})
        ).status_code
        == 404
    )

    first.refresh_from_db()
    assert first.is_active is True


def test_saved_methods_require_authentication(api_client, db) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:payments:methods")).status_code in (401, 403)


# ── Expiry is display only ────────────────────────────────────────────────────


def test_an_expired_card_is_flagged(verified_user, db) -> None:  # type: ignore[no-untyped-def]
    """Display only — the provider is the authority on whether a token works."""
    method = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_old",
        card_last4="4242",
        card_exp_month="01",
        card_exp_year="2020",
    )
    assert method.is_expired is True

    future = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_new",
        card_last4="4243",
        card_exp_month="12",
        card_exp_year="2099",
    )
    assert future.is_expired is False


def test_a_card_with_no_expiry_is_not_treated_as_expired(verified_user, db) -> None:  # type: ignore[no-untyped-def]
    method = SavedPaymentMethod.objects.create(
        user=verified_user, provider="bank_transfer", authorization_code="AUTH_bank"
    )
    assert method.is_expired is False
    assert method.label == "Bank transfer"


def test_a_two_digit_year_is_understood(verified_user, db) -> None:  # type: ignore[no-untyped-def]
    method = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_2y",
        card_last4="4242",
        card_exp_month="01",
        card_exp_year="20",
    )
    assert method.is_expired is True


def test_string_representation(verified_user, db) -> None:  # type: ignore[no-untyped-def]
    method = SavedPaymentMethod.objects.create(
        user=verified_user,
        provider="paystack",
        authorization_code="AUTH_s",
        card_last4="4242",
        card_brand="visa",
    )
    assert str(method) == "visa ••••4242"
