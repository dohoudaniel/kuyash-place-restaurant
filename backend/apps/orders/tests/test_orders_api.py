"""Order API: placement, polling and access control."""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

from apps.orders.models import Order, OrderStatus
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


def place_via_api(api_client, key=None, **body):  # type: ignore[no-untyped-def]
    return api_client.post(
        reverse("v1:orders:create"),
        {"payment_method": "card", **body},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
    )


def test_placing_an_order(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = place_via_api(api_client)
    assert response.status_code == 201

    body = response.json()
    assert body["reference"].startswith("KYS-")
    assert body["status"] == "pending_payment"
    assert body["totals"]["grand_total"]["amount"] == 2_180_000
    assert body["timeline"][0]["status"] == "pending_payment"


def test_an_idempotency_key_is_required(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:orders:create"), {"payment_method": "card"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


def test_a_double_submit_creates_one_order(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    """A double-tapped Confirm button must not take two payments."""
    api_client.force_authenticate(user=verified_user)
    key = str(uuid.uuid4())

    first = place_via_api(api_client, key=key)
    second = place_via_api(api_client, key=key)

    assert first.status_code == second.status_code == 201
    assert first.json()["reference"] == second.json()["reference"]
    assert second["Idempotency-Replayed"] == "true"
    assert Order.objects.count() == 1


def test_a_failed_attempt_releases_the_key_for_retry(  # type: ignore[no-untyped-def]
    api_client, verified_user, ready_cart
) -> None:
    api_client.force_authenticate(user=verified_user)
    key = str(uuid.uuid4())

    blocked = place_via_api(api_client, key=key, expected_total=1)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "price_changed"

    # Same key, corrected request: must be allowed through.
    retried = place_via_api(api_client, key=key)
    assert retried.status_code == 201


def test_a_client_cannot_dictate_the_total(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    body = place_via_api(
        api_client, grand_total=1, subtotal=1, discount_total=999_999, vat_total=0
    ).json()
    assert body["totals"]["grand_total"]["amount"] == 2_180_000
    assert body["totals"]["discount"]["amount"] == 0


def test_order_detail_is_etag_cached(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Polling every 15s should cost nothing while nothing has happened."""
    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]
    url = reverse("v1:orders:detail", kwargs={"reference": reference})

    first = api_client.get(url)
    assert first.status_code == 200
    etag = first["ETag"]

    unchanged = api_client.get(url, HTTP_IF_NONE_MATCH=etag)
    assert unchanged.status_code == 304

    transition(Order.objects.get(reference=reference), OrderStatus.PAID)
    changed = api_client.get(url, HTTP_IF_NONE_MATCH=etag)
    assert changed.status_code == 200
    assert changed["ETag"] != etag


def test_another_user_cannot_read_an_order(api_client, verified_user, ready_cart, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]

    intruder = User.objects.create_user(
        email="mallory@example.com", password="correct-horse-battery-staple"
    )
    api_client.force_authenticate(user=intruder)
    response = api_client.get(reverse("v1:orders:detail", kwargs={"reference": reference}))
    # 404, not 403: existence itself is not disclosed.
    assert response.status_code == 404


def test_references_are_not_enumerable(api_client, db) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:orders:detail", kwargs={"reference": "KYS-AAAAAA"}))
    assert response.status_code == 404


def test_a_guest_reads_their_order_with_the_token(api_client, branch, category, cart) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.models import FulfilmentType
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem

    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    svc.add_item(cart=cart, item_slug="burger")
    cart.fulfilment_type = FulfilmentType.PICKUP
    cart.save()

    created = api_client.post(
        reverse("v1:orders:create"),
        {
            "payment_method": "cash",
            "guest": {
                "email": "guest@example.com",
                "phone": "+2348012345678",
                "full_name": "Guest",
            },
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_X_CART_TOKEN=cart.session_token,
    ).json()

    url = reverse("v1:orders:detail", kwargs={"reference": created["reference"]})
    assert api_client.get(url).status_code == 404
    assert api_client.get(url, HTTP_X_GUEST_TOKEN=created["guest_token"]).status_code == 200
    assert api_client.get(url, HTTP_X_GUEST_TOKEN="wrong-token").status_code == 404


def test_order_history_is_scoped_to_the_caller(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    place_via_api(api_client)

    body = api_client.get(reverse("v1:orders:history")).json()
    assert len(body["results"]) == 1
    assert body["results"][0]["item_count"] == 2


def test_history_requires_authentication(api_client, db) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:orders:history")).status_code in (401, 403)


def test_a_customer_can_cancel_before_cooking(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]

    response = api_client.post(
        reverse("v1:orders:cancel", kwargs={"reference": reference}),
        {"reason": "Changed my mind"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_a_customer_cannot_cancel_once_cooking(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]
    order = Order.objects.get(reference=reference)
    for status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
        transition(order, status)

    response = api_client.post(
        reverse("v1:orders:cancel", kwargs={"reference": reference}), {}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "illegal_transition"


def test_staff_may_read_any_order(api_client, verified_user, ready_cart, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    """The kitchen has to be able to look an order up when a customer phones."""
    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]

    api_client.force_authenticate(user=kitchen_user)
    response = api_client.get(reverse("v1:orders:detail", kwargs={"reference": reference}))
    assert response.status_code == 200


def test_a_stranger_cannot_cancel_someone_elses_order(  # type: ignore[no-untyped-def]
    api_client, verified_user, ready_cart
) -> None:
    api_client.force_authenticate(user=verified_user)
    reference = place_via_api(api_client).json()["reference"]

    api_client.force_authenticate(user=None)
    response = api_client.post(
        reverse("v1:orders:cancel", kwargs={"reference": reference}), {}, format="json"
    )
    assert response.status_code == 404
    assert Order.objects.get(reference=reference).status != OrderStatus.CANCELLED


def test_order_history_rows_carry_a_short_preview(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    """A history card shows what was ordered without one request per order."""
    from apps.orders.services.placement import place_order

    place_order(cart=ready_cart, payment_method="card")
    api_client.force_authenticate(verified_user)

    row = api_client.get(reverse("v1:orders:history")).json()["results"][0]

    assert row["preview"][0]["name"] == "Classic Smash Burger"
    assert row["preview"][0]["quantity"] == 2
    assert row["preview"][0]["line_subtotal"]["display"].startswith("₦")
    assert len(row["preview"]) <= 2
