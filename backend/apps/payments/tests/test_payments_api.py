"""Payment API endpoints."""

from __future__ import annotations

import json

import pytest
import responses
from django.urls import reverse

from apps.orders.models import OrderStatus
from apps.payments.models import TransactionStatus

pytestmark = pytest.mark.django_db

INIT_URL = "https://api.paystack.co/transaction/initialize"
VERIFY_URL = "https://api.paystack.co/transaction/verify/"


def mock_init() -> None:
    responses.add(
        responses.POST,
        INIT_URL,
        json={
            "status": True,
            "data": {"authorization_url": "https://checkout.paystack.com/x", "reference": "r"},
        },
        status=200,
    )


def mock_verify(reference: str, amount: int) -> None:
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
                "authorization": {"last4": "4242"},
            },
        },
        status=200,
    )


@responses.activate
def test_initialise_endpoint(api_client, verified_user, order, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    mock_init()
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:payments:initialise"), {"order": order.reference}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["authorization_url"].startswith("https://checkout.paystack.com/")
    assert body["amount"]["amount"] == order.grand_total


def test_initialise_refuses_someone_elses_order(api_client, order, paystack_keys, db) -> None:  # type: ignore[no-untyped-def]
    """404, not 403: the existence of an order is not disclosed."""
    from apps.accounts.models import User

    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=intruder)
    response = api_client.post(
        reverse("v1:payments:initialise"), {"order": order.reference}, format="json"
    )
    assert response.status_code == 404


@responses.activate
def test_card_details_in_a_request_body_go_nowhere(  # type: ignore[no-untyped-def]
    api_client, verified_user, order, paystack_keys
) -> None:
    """Card fields sent by a client are discarded, not forwarded.

    The serializer has no such fields, so they never reach a service, are never
    persisted, and are never included in the provider request.
    """
    mock_init()
    api_client.force_authenticate(user=verified_user)

    response = api_client.post(
        reverse("v1:payments:initialise"),
        {
            "order": order.reference,
            "card_number": "4242424242424242",
            "cvv": "123",
            "expiry": "12/29",
        },
        format="json",
    )
    assert response.status_code == 201

    # Nothing card-shaped reached the provider.
    sent = responses.calls[0].request.body
    sent_text = sent.decode() if isinstance(sent, bytes) else str(sent)
    assert "4242424242424242" not in sent_text
    assert "cvv" not in sent_text.lower()

    # Nor was any of it persisted.
    from apps.payments.models import PaymentTransaction

    for record in PaymentTransaction.objects.all():
        assert "4242424242424242" not in json.dumps(record.raw_response)
        assert record.card_last4 == ""


@responses.activate
def test_verify_endpoint_settles(api_client, transaction, paystack_keys, verified_user) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    api_client.force_authenticate(user=verified_user)
    response = api_client.get(
        reverse("v1:payments:verify", kwargs={"reference": transaction.our_reference})
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == TransactionStatus.SUCCESS
    assert body["order_status"] == OrderStatus.PAID


def test_verify_unknown_reference_is_404(api_client, db, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:payments:verify", kwargs={"reference": "KYS-NOPE-0000"}))
    assert response.status_code == 404


def test_verify_refuses_someone_elses_payment(api_client, transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    """404, not 403 — and no provider call at all.

    This endpoint had no ownership check: a reference was enough to read any
    order's status, and to spend one outbound provider call per request doing
    it. No response is registered here, so the autouse HTTP guard fails the test
    if anything reaches the network.
    """
    from apps.accounts.models import User

    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=intruder)

    response = api_client.get(
        reverse("v1:payments:verify", kwargs={"reference": transaction.our_reference})
    )

    assert response.status_code == 404
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.PENDING


@responses.activate
def test_a_guest_verifies_their_own_payment_with_their_token(  # type: ignore[no-untyped-def]
    api_client, ready_cart, paystack_keys
) -> None:
    """Guest checkout has no session; the token is how a guest proves it is theirs."""
    from django.utils import timezone

    from apps.carts.models import FulfilmentType
    from apps.orders.services.placement import place_order
    from apps.payments.models import PaymentTransaction

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
    )
    url = reverse("v1:payments:verify", kwargs={"reference": record.our_reference})

    assert api_client.get(url).status_code == 404

    mock_verify(record.our_reference, record.amount)
    response = api_client.get(url, HTTP_X_GUEST_TOKEN=order.guest_token)

    assert response.status_code == 200
    assert response.json()["order_status"] == OrderStatus.PAID


@responses.activate
def test_verify_is_rate_limited(  # type: ignore[no-untyped-def]
    api_client, transaction, paystack_keys, verified_user, throttle_rates
) -> None:
    """Every call here is an outbound provider call on our own account."""
    mock_verify(transaction.our_reference, transaction.amount)
    api_client.force_authenticate(user=verified_user)
    url = reverse("v1:payments:verify", kwargs={"reference": transaction.our_reference})

    with throttle_rates(anon="1/min"):
        first = api_client.get(url)
        second = api_client.get(url)

    assert first.status_code == 200
    assert second.status_code == 429


def test_the_webhook_endpoint_is_rate_limited(api_client, paystack_keys, throttle_rates) -> None:  # type: ignore[no-untyped-def]
    """Unauthenticated by design is not the same as unlimited."""
    url = reverse("v1:webhooks:paystack")
    payload = {"event": "charge.success", "data": {"id": 1}}

    with throttle_rates(anon="1/min"):
        first = api_client.post(url, payload, format="json")
        second = api_client.post(url, payload, format="json")

    assert first.status_code == 401  # unsigned: let through to be judged, then refused
    assert second.status_code == 429  # never even judged


def test_webhook_endpoints_are_unauthenticated_but_signature_gated(  # type: ignore[no-untyped-def]
    api_client, transaction, paystack_keys
) -> None:
    """WH-5: the signature is the authentication, so no session is needed —
    but an unsigned request is refused."""
    response = api_client.post(
        reverse("v1:webhooks:paystack"),
        {"event": "charge.success", "data": {"id": 1, "reference": transaction.our_reference}},
        format="json",
    )
    assert response.status_code == 401


@responses.activate
def test_a_signed_webhook_is_accepted(client, transaction, paystack_keys) -> None:  # type: ignore[no-untyped-def]
    import hashlib
    import hmac

    mock_verify(transaction.our_reference, transaction.amount)
    payload = json.dumps(
        {"event": "charge.success", "data": {"id": "evt-9", "reference": transaction.our_reference}}
    ).encode()
    signature = hmac.new(paystack_keys.encode(), payload, hashlib.sha512).hexdigest()

    response = client.post(
        reverse("v1:webhooks:paystack"),
        data=payload,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=signature,
    )
    assert response.status_code == 200
    transaction.refresh_from_db()
    assert transaction.status == TransactionStatus.SUCCESS


@responses.activate
def test_refund_requires_a_manager(
    api_client, transaction, paystack_keys, kitchen_user, verified_user
) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    from apps.payments.services.payments import verify_and_settle

    verify_and_settle(transaction)
    url = reverse("v1:payments:refund", kwargs={"reference": transaction.order.reference})

    api_client.force_authenticate(user=verified_user)
    assert api_client.post(url, {}, format="json").status_code == 403

    api_client.force_authenticate(user=kitchen_user)
    assert api_client.post(url, {}, format="json").status_code == 403


@responses.activate
def test_a_manager_can_refund(api_client, transaction, paystack_keys, manager_user) -> None:  # type: ignore[no-untyped-def]
    mock_verify(transaction.our_reference, transaction.amount)
    from apps.payments.services.payments import verify_and_settle

    verify_and_settle(transaction)
    responses.add(
        responses.POST,
        "https://api.paystack.co/refund",
        json={"status": True, "data": {"id": 5}},
        status=200,
    )

    api_client.force_authenticate(user=manager_user)
    response = api_client.post(
        reverse("v1:payments:refund", kwargs={"reference": transaction.order.reference}),
        {"reason": "Kitchen could not fulfil"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["order_status"] == OrderStatus.REFUNDED


# ──────────────────────────────────────────────────────────────────────────────
# Card-saving consent, driven through the endpoint
# ──────────────────────────────────────────────────────────────────────────────
#
# The saved-card tests set `save_method` on the model directly, so none of them
# noticed the serializer never declared `save_card`: the view read a key that
# validation always dropped, and consent could not be given at all.


@responses.activate
def test_initialise_does_not_keep_a_card_without_consent(  # type: ignore[no-untyped-def]
    api_client, verified_user, order, paystack_keys
) -> None:
    from apps.payments.models import PaymentTransaction

    mock_init()
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:payments:initialise"), {"order": order.reference}, format="json"
    )

    assert response.status_code == 201
    assert (
        PaymentTransaction.objects.get(our_reference=response.json()["reference"]).save_method
        is False
    )


@responses.activate
def test_initialise_records_consent_to_keep_the_card(  # type: ignore[no-untyped-def]
    api_client, verified_user, order, paystack_keys
) -> None:
    from apps.payments.models import PaymentTransaction

    mock_init()
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:payments:initialise"),
        {"order": order.reference, "save_card": True},
        format="json",
    )

    assert response.status_code == 201
    assert (
        PaymentTransaction.objects.get(our_reference=response.json()["reference"]).save_method
        is True
    )


@pytest.mark.django_db
def test_verify_reports_the_order_as_paid_in_the_same_response(
    api_client, verified_user, order, settings
) -> None:  # type: ignore[no-untyped-def]
    """The response used to say `payment_status: pending` for an order it had just
    marked paid — it read an order instance cached before settlement."""
    from apps.payments.services.payments import initialise_payment

    settings.DEBUG = True
    settings.PAYSTACK_SECRET_KEY = ""
    settings.FLUTTERWAVE_SECRET_KEY = ""
    record = initialise_payment(order=order)

    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:payments:verify", args=[record.our_reference])).json()

    assert body["status"] == "success"
    assert body["order_status"] == "paid"
    assert body["payment_status"] == "paid"
