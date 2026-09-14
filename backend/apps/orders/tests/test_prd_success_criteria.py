"""PRD §9 — the Phase 1 success criteria, demonstrated end to end.

One customer journey through the real API, in the order a person would live it:
register, verify, browse a menu staff control, build a cart on one device and
find it on another, check out, pay on the provider's hosted page, and watch the
kitchen take the order through to the door. Each assertion names the criterion
it demonstrates.

Criterion 11 (no ``alert()`` in any submission path) is a property of the
frontend source, so it is enforced by ``scripts/check-no-alert.sh`` in CI rather
than here.

The individual rules have their own focused suites; this file is the proof that
they hold *together*, through HTTP, as one journey.
"""

from __future__ import annotations

import contextlib
import io
import re
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.carts.models import Cart, CartStatus
from apps.catalog.models import MenuItem, MenuItemImage, Modifier, ModifierGroup
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction
from apps.realtime import broadcast, payloads

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-battery-staple"
MONEY_KEYS = {"amount", "currency", "display"}


# ── Helpers ───────────────────────────────────────────────────────────────────


def png() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, "PNG")
    return SimpleUploadedFile("burger.png", buffer.getvalue(), content_type="image/png")


def rows(body: Any) -> list[dict[str, Any]]:
    """A list endpoint's rows, whether or not it is paginated."""
    if isinstance(body, dict):
        for key in ("results", "items", "orders"):
            if isinstance(body.get(key), list):
                return list(body[key])
    return list(body)


def verification_key() -> str:
    body = Notification.objects.get(template_key="verify_email").body
    match = re.search(r"verify-email\?key=([^\s]+)", body)
    assert match, "the verification email carries a link"
    return match.group(1)


@contextlib.contextmanager
def request_commits() -> Iterator[None]:
    """Commit what one request did, as production would.

    The test database wraps the whole test in a single transaction, so nothing
    ever commits and every ``on_commit`` push would stay pending — and the
    one-push-per-order-per-transaction rule would then drop later pushes as
    duplicates of the first. In production each request is its own
    transaction. This runs the callbacks a block queued, then forgets them.
    """
    connection = transaction.get_connection()
    start = len(connection.run_on_commit)
    yield
    while len(connection.run_on_commit) > start:
        pending = connection.run_on_commit[start:]
        del connection.run_on_commit[start:]
        for _savepoints, callback, *_rest in pending:
            callback()


class RecordingLayer:
    """Stands in for the channel layer and remembers which groups were told."""

    def __init__(self) -> None:
        self.groups: list[str] = []

    async def group_send(self, group: str, message: dict[str, Any]) -> None:
        self.groups.append(group)


@pytest.fixture
def staff_menu(branch, category):  # type: ignore[no-untyped-def]
    """A dish as a manager would set it up in the Django admin."""
    burger = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Classic Smash Burger",
        slug="classic-smash-burger",
        base_price=1_090_000,  # ₦10,900.00
        needs_repricing=False,
        prep_time_minutes=18,
    )
    MenuItemImage.objects.create(item=burger, image=png(), alt_text="Smash burger", is_primary=True)
    extras = ModifierGroup.objects.create(item=burger, name="Extras", min_select=0, max_select=3)
    cheese = Modifier.objects.create(group=extras, name="Extra cheese", price_delta=30_000)
    return burger, cheese


# ── The journey ───────────────────────────────────────────────────────────────


def test_the_phase_one_success_criteria_hold_end_to_end(  # type: ignore[no-untyped-def]
    branch,
    zone,
    staff_menu,
    kitchen_user,
    settings,
    monkeypatch,
) -> None:
    burger, cheese = staff_menu
    phone = APIClient()

    # ── 1. Register, verify, sign in, see your own name ───────────────────────
    registered = phone.post(
        reverse("v1:auth:register"),
        {
            "email": "ada@example.com",
            "password": PASSWORD,
            "full_name": "Ada Obi",
            "phone": "+2348012345678",
            "accept_terms": True,
        },
        format="json",
    )
    assert registered.status_code == 201, "(1) registration succeeds"
    assert registered.json()["email_verification_required"] is True

    verified = phone.post(
        reverse("v1:auth:verify-email"), {"key": verification_key()}, format="json"
    )
    assert verified.status_code == 200, "(1) the emailed link verifies the address"

    session_user = phone.get(reverse("v1:auth:session")).json()["user"]
    assert session_user["full_name"] == "Ada Obi", "(1) the customer sees their own name"
    assert session_user["full_name"] != "John Doe"
    assert phone.get(reverse("v1:accounts:me")).json()["full_name"] == "Ada Obi"

    # ── 2. A menu whose prices, availability and photos staff control ─────────
    assert MenuItem in admin.site._registry, "(2) dishes are managed in the Django admin"
    detail_url = reverse("v1:catalog:item-detail", kwargs={"slug": burger.slug})
    dish = phone.get(detail_url).json()
    assert dish["price"]["amount"] == 1_090_000, "(2) the price is the one staff set"
    offered = dish["modifier_groups"][0]["modifiers"][0]
    assert offered["price_delta"]["amount"] == 30_000, "(3) modifiers carry real prices"
    assert dish["image_url"], "(2) the photo is the one staff uploaded"
    assert dish["is_available"] is True

    burger.is_available_now = False  # staff mark it sold out …
    burger.save(update_fields=["is_available_now"])
    listed = next(
        (
            row
            for row in rows(phone.get(reverse("v1:catalog:items")).json())
            if row["slug"] == burger.slug
        ),
        None,
    )
    assert listed is None or listed["is_available"] is False, "(2) a sold-out dish is not offered"
    burger.is_available_now = True  # … and back on
    burger.save(update_fields=["is_available_now"])

    # ── 3. Priced modifiers, in a cart that follows the customer ──────────────
    added = phone.post(
        reverse("v1:carts:items"),
        {
            "menu_item": burger.slug,
            "quantity": 2,
            "modifiers": [{"modifier": str(cheese.id)}],
            "unit_price": 1,  # a tampered client
        },
        format="json",
    )
    assert added.status_code == 201
    line = added.json()["items"][0]
    assert line["unit_price"]["amount"] == 1_120_000, (
        "(3) the modifier is priced; (4) the client's price is ignored"
    )

    laptop = APIClient()
    signed_in = laptop.post(
        reverse("v1:auth:login"), {"email": "ada@example.com", "password": PASSWORD}, format="json"
    )
    assert signed_in.status_code == 200
    on_laptop = laptop.get(reverse("v1:carts:cart")).json()
    assert [item["unit_price"]["amount"] for item in on_laptop["items"]] == [1_120_000], (
        "(3) the cart survives switching devices"
    )

    # ── 4. Every figure comes from the server ─────────────────────────────────
    address = laptop.post(
        reverse("v1:accounts:addresses"),
        {
            "label": "home",
            "recipient_name": "Ada Obi",
            "phone": "+2348012345678",
            "street": "12 Adeola Odeku Street",
            "area": "Victoria Island",
            "city": "Lagos",
            "state": "Lagos",
            "is_default": True,
        },
        format="json",
    ).json()
    assert address["is_deliverable"] is True

    # ── 5. A promo validates server-side and cannot be enumerated ─────────────
    from apps.promotions.models import DiscountType, PromoCode

    PromoCode.objects.create(
        branch=branch,
        code="WELCOME10",
        discount_type=DiscountType.PERCENTAGE,
        value=1000,
        usage_limit=1,
    )
    assert (
        laptop.post(reverse("v1:carts:promo"), {"code": "GUESS1"}, format="json").json()["code"]
        == "promo_invalid"
    )
    promo = laptop.post(reverse("v1:carts:promo"), {"code": "welcome10"}, format="json")
    assert promo.status_code == 200, "(5) the code is checked by the server"

    checkout = laptop.patch(
        reverse("v1:carts:fulfilment"),
        {"fulfilment_type": "delivery", "delivery_address": address["id"], "tip": 50_000},
        format="json",
    ).json()
    totals = checkout["totals"]
    for figure in ("subtotal", "discount", "delivery_fee", "vat", "tip", "grand_total"):
        assert set(totals[figure]) >= MONEY_KEYS, f"(4) {figure} is a server-formatted Money"
    assert totals["subtotal"]["amount"] == 2_240_000
    assert totals["discount"]["amount"] == 224_000, "(5) 10% off, computed by the server"
    assert totals["tip"]["amount"] == 50_000
    server_total = totals["grand_total"]["amount"]

    # ── 7. The order exists, with a server reference, before the cart clears ──
    with request_commits():
        placed = laptop.post(
            reverse("v1:orders:create"),
            {
                "payment_method": "card",
                "reference": "KYS-MINE-0001",
                "grand_total": 1,
                "subtotal": 1,
                "discount_total": 999_999,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert placed.status_code == 201
    order_body = placed.json()
    reference = order_body["reference"]
    assert reference != "KYS-MINE-0001" and reference.startswith("KYS-"), (
        "(7) the server generates the reference"
    )
    assert order_body["totals"]["grand_total"]["amount"] == server_total, (
        "(4) tampering with the totals changes nothing"
    )
    assert Order.objects.filter(reference=reference).exists(), "(7) the order is in the database"
    assert (
        Cart.objects.get(user__email="ada@example.com", branch=branch).status
        == CartStatus.CONVERTED
    )
    assert laptop.get(reverse("v1:carts:cart")).json()["items"] == [], (
        "(7) only then is the cart empty"
    )

    # ── 6. Hosted checkout; no card data reaches our servers ──────────────────
    settings.DEBUG = True  # the simulator stands in for Paystack's hosted page
    settings.PAYSTACK_SECRET_KEY = ""
    settings.FLUTTERWAVE_SECRET_KEY = ""
    started = laptop.post(
        reverse("v1:payments:initialise"),
        {"order": reference, "card_number": "4242424242424242", "cvv": "123", "expiry": "12/29"},
        format="json",
    )
    assert started.status_code == 201
    assert started.json()["authorization_url"], "(6) the customer is sent to a hosted page"
    record = PaymentTransaction.objects.get(order__reference=reference)
    stored = " ".join(str(getattr(record, field.attname)) for field in record._meta.concrete_fields)
    assert "4242424242424242" not in stored and "12/29" not in stored, "(6) no card data is stored"
    column_names = {field.name for field in record._meta.fields}
    assert not column_names & {"card_number", "cvv", "pan", "expiry"}, (
        "(6) there is nowhere to store it"
    )

    # ── 8. The kitchen sees it at once, and is told without refreshing ────────
    layer = RecordingLayer()
    monkeypatch.setattr(broadcast, "get_channel_layer", lambda: layer)
    with request_commits():
        verify_url = reverse("v1:payments:verify", kwargs={"reference": record.our_reference})
        paid = APIClient().get(verify_url).json()  # the provider's redirect lands here
    assert paid["order_status"] == "paid"
    assert payloads.kitchen_group(branch.id) in layer.groups, (
        "(8) the kitchen screen is pushed the ticket"
    )

    kitchen = APIClient()
    kitchen.force_authenticate(user=kitchen_user)
    ticket = next(
        t
        for t in kitchen.get(reverse("v1:kds:queue")).json()["orders"]
        if t["reference"] == reference
    )
    assert ticket["elapsed_seconds"] < 15, "(8) on the KDS within 15 seconds"
    assert ticket["items"][0]["modifiers"] == ["Extra cheese"]

    # ── 8 & 9. Advanced to delivered; the customer sees every step ────────────
    order_url = reverse("v1:orders:detail", kwargs={"reference": reference})
    steps = [
        ("accept", None, "confirmed"),
        ("advance", "preparing", "preparing"),
        ("advance", "ready", "ready"),
        ("advance", "out_for_delivery", "out_for_delivery"),
        ("advance", "delivered", "delivered"),
    ]
    for action, target, expected in steps:
        with request_commits():
            moved = kitchen.post(
                reverse("v1:kds:transition", kwargs={"reference": reference, "action": action}),
                {"to": target} if target else {},
                format="json",
            )
        assert moved.status_code == 200, f"(8) the kitchen can move the order to {expected}"
        seen = laptop.get(order_url).json()
        assert seen["status"] == expected, f"(9) /orders/{reference} shows {expected}"

    timeline = [step["status"] for step in seen["timeline"]]
    assert {"paid", "confirmed", "out_for_delivery", "delivered"} <= set(timeline)

    emails = Notification.objects.filter(recipient="ada@example.com")
    sent = set(emails.values_list("template_key", flat=True))
    assert "order_confirmation" in sent, "(9) an email at confirmation"
    assert "order_out_for_delivery" in sent, "(9) an email at dispatch"
    assert reference in emails.get(template_key="order_confirmation").body

    # ── 10. A real, server-backed order history ───────────────────────────────
    history = rows(laptop.get(reverse("v1:orders:history")).json())
    assert [row["reference"] for row in history] == [reference], "(10) the order is in the history"
    assert APIClient().get(reverse("v1:orders:history")).status_code in (401, 403), (
        "(10) history belongs to a signed-in customer"
    )

    # ── 5 (continued). Usage limits hold for the next customer ────────────────
    from apps.accounts.models import User

    User.objects.create_user(
        email="bola@example.com", password=PASSWORD, full_name="Bola", is_active=True
    )
    other = APIClient()
    other.force_authenticate(user=User.objects.get(email="bola@example.com"))
    other.post(reverse("v1:carts:items"), {"menu_item": burger.slug, "quantity": 1}, format="json")
    reused = other.post(reverse("v1:carts:promo"), {"code": "WELCOME10"}, format="json")
    assert reused.status_code == 422, "(5) a code used up is refused"


def test_promo_codes_cannot_be_enumerated(api_client, branch, staff_menu, throttle_rates) -> None:  # type: ignore[no-untyped-def]
    """(5) No endpoint lists codes, a wrong guess says nothing specific.

    Guessing is rate-limited.
    """
    from django.urls import NoReverseMatch

    for name in ("v1:carts:promos", "v1:promotions:list", "v1:carts:promo-list"):
        with pytest.raises(NoReverseMatch):
            reverse(name)

    burger, _ = staff_menu
    token = api_client.post(reverse("v1:carts:items"), {"menu_item": burger.slug}, format="json")[
        "X-Cart-Token"
    ]
    with throttle_rates(promo_apply="3/min"):
        codes = [
            api_client.post(
                reverse("v1:carts:promo"),
                {"code": f"GUESS{index}"},
                format="json",
                HTTP_X_CART_TOKEN=token,
            ).status_code
            for index in range(6)
        ]
    assert codes[:3] == [422, 422, 422]
    assert 429 in codes, "(5) guessing codes is throttled"
