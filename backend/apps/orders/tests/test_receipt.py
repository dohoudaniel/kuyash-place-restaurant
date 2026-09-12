"""PDF receipts.

Two things are actually worth testing here, and neither is layout: that a
receipt is only issued for money that was received, and that the amounts on it
are the ones the customer was charged — including the naira sign surviving the
trip into a PDF, which it does not do on its own.
"""

from __future__ import annotations

import base64
import re
import zlib

import pytest
from django.urls import reverse

from apps.common.money import format_money, format_money_ascii
from apps.orders.models import PaymentStatus
from apps.orders.services.placement import place_order
from apps.orders.services.receipt import OrderNotPaid, render_receipt_pdf

pytestmark = pytest.mark.django_db


def text_of(pdf: bytes) -> str:
    """Everything drawn on the page, as one string.

    Crude but sufficient, and cheaper than a PDF parser dependency: reportlab
    writes each `drawString` as a `(literal) Tj` in the content stream. The
    streams are ASCII85-then-Flate encoded by default, so both come off first.
    """
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        raw = match.group(1).strip()
        if raw.endswith(b"~>"):
            raw = base64.a85decode(raw, adobe=True)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        chunks.extend(
            _unescape(piece.decode("latin-1"))
            for piece in re.findall(rb"\((.*?)\)\s*Tj", raw, re.S)
        )
    return "\n".join(chunks)


def _unescape(literal: str) -> str:
    """Undo PDF string escaping: `\\(`, `\\)`, `\\\\` and octal codes."""
    literal = re.sub(r"\\([0-7]{1,3})", lambda m: chr(int(m.group(1), 8)), literal)
    return literal.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")


@pytest.fixture
def paid_order(ready_cart):  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    order.payment_status = PaymentStatus.PAID
    order.amount_paid = order.grand_total
    order.save(update_fields=["payment_status", "amount_paid"])
    return order


# ──────────────────────────────────────────────────────────────────────────────
# What may be receipted
# ──────────────────────────────────────────────────────────────────────────────


def test_an_unpaid_order_has_no_receipt(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """A document headed "Receipt" for money never received causes the dispute
    it is supposed to settle."""
    order = place_order(cart=ready_cart, payment_method="card")
    with pytest.raises(OrderNotPaid):
        render_receipt_pdf(order)


def test_a_paid_order_renders_a_pdf(paid_order) -> None:  # type: ignore[no-untyped-def]
    pdf = render_receipt_pdf(paid_order)
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")


# ──────────────────────────────────────────────────────────────────────────────
# The numbers
# ──────────────────────────────────────────────────────────────────────────────


def test_the_receipt_states_the_reference_and_the_total(paid_order) -> None:  # type: ignore[no-untyped-def]
    body = text_of(render_receipt_pdf(paid_order))
    assert paid_order.reference in body
    assert format_money_ascii(paid_order.grand_total) in body
    assert format_money_ascii(paid_order.subtotal) in body


def test_money_is_written_with_the_iso_code_not_the_naira_sign(paid_order) -> None:  # type: ignore[no-untyped-def]
    """The regression this exists for.

    The standard PDF fonts use WinAnsiEncoding, which has no U+20A6. reportlab
    substitutes it silently, so ``₦21,800.00`` prints as ``n21,800.00`` — a
    mangled amount on a financial document. Money goes in as ``NGN 21,800.00``.
    """
    body = text_of(render_receipt_pdf(paid_order))
    assert "NGN " in body
    assert "₦" not in body
    # And the display string the API returns is *not* what was drawn.
    assert format_money(paid_order.grand_total) not in body


def test_the_lines_appear_with_their_quantities(paid_order) -> None:  # type: ignore[no-untyped-def]
    body = text_of(render_receipt_pdf(paid_order))
    assert "2x Classic Smash Burger" in body


def test_the_receipt_prints_the_rate_that_applied_then_not_today(paid_order) -> None:  # type: ignore[no-untyped-def]
    """The order snapshots its own VAT rate. Changing the branch must not
    rewrite a receipt that was already issued."""
    paid_order.vat_rate_bps = 500
    paid_order.save(update_fields=["vat_rate_bps"])
    paid_order.branch.vat_rate_bps = 750
    paid_order.branch.save(update_fields=["vat_rate_bps"])

    body = text_of(render_receipt_pdf(paid_order))
    assert "5%" in body
    assert "7.5%" not in body


def test_the_tax_note_follows_the_direction_the_order_was_charged_at(paid_order) -> None:  # type: ignore[no-untyped-def]
    body = text_of(render_receipt_pdf(paid_order))
    assert "include VAT" in body

    paid_order.prices_included_vat = False
    paid_order.save(update_fields=["prices_included_vat"])
    assert "was added to the item prices" in text_of(render_receipt_pdf(paid_order))


def test_optional_lines_are_omitted_when_zero(paid_order) -> None:  # type: ignore[no-untyped-def]
    body = text_of(render_receipt_pdf(paid_order))
    assert "Tip" not in body
    assert "Service charge" not in body


def test_a_discount_names_the_code_that_gave_it(paid_order) -> None:  # type: ignore[no-untyped-def]
    paid_order.discount_total = 100_000
    paid_order.promo_code_snapshot = "WELCOME10"
    paid_order.tip = 50_000
    paid_order.service_charge = 25_000
    paid_order.delivery_fee = 150_000
    paid_order.save()

    body = text_of(render_receipt_pdf(paid_order))
    assert "Discount (WELCOME10)" in body
    assert f"-{format_money_ascii(100_000)}" in body
    assert "Tip" in body
    assert "Service charge" in body
    assert "Delivery" in body


def test_modifiers_and_notes_are_printed(ready_cart, branch) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem, Modifier, ModifierGroup

    item = MenuItem.objects.get(slug="classic-smash-burger")
    group = ModifierGroup.objects.create(item=item, name="Extras", min_select=0, max_select=2)
    modifier = Modifier.objects.create(group=group, name="Extra cheese", price_delta=50_000)

    ready_cart.items.all().delete()
    svc.add_item(
        cart=ready_cart,
        item_slug=item.slug,
        quantity=1,
        modifiers=[{"modifier": str(modifier.id), "quantity": 1}],
        special_instructions="Well done, please.",
    )
    order = place_order(cart=ready_cart, payment_method="card")
    order.payment_status = PaymentStatus.PAID
    order.amount_paid = order.grand_total
    order.save(update_fields=["payment_status", "amount_paid"])

    body = text_of(render_receipt_pdf(order))
    assert "Extra cheese" in body
    assert "Well done, please." in body


def test_a_size_is_printed_beside_the_dish(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Without it, two lines at different prices look like a pricing error."""
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem, Variant

    item = MenuItem.objects.get(slug="classic-smash-burger")
    variant = Variant.objects.create(item=item, name="Large", price_delta=200_000)

    ready_cart.items.all().delete()
    svc.add_item(cart=ready_cart, item_slug=item.slug, quantity=1, variant_id=str(variant.id))
    order = place_order(cart=ready_cart, payment_method="card")
    order.payment_status = PaymentStatus.PAID
    order.amount_paid = order.grand_total
    order.save(update_fields=["payment_status", "amount_paid"])

    assert "1x Classic Smash Burger (Large)" in text_of(render_receipt_pdf(order))


def test_a_long_order_spills_onto_a_second_page(ready_cart, branch, category) -> None:  # type: ignore[no-untyped-def]
    """Forty lines must not print off the bottom of the sheet."""
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem

    ready_cart.items.all().delete()
    for index in range(40):
        MenuItem.objects.create(
            branch=branch,
            category=category,
            name=f"Dish {index}",
            slug=f"dish-{index}",
            base_price=250_000,
            needs_repricing=False,
        )
        svc.add_item(cart=ready_cart, item_slug=f"dish-{index}", quantity=1)

    order = place_order(cart=ready_cart, payment_method="card")
    order.payment_status = PaymentStatus.PAID
    order.amount_paid = order.grand_total
    order.save(update_fields=["payment_status", "amount_paid"])

    pdf = render_receipt_pdf(order)
    assert pdf.count(b"/Type /Page\n") >= 2
    body = text_of(pdf)
    assert "Dish 0" in body
    assert "Dish 39" in body
    assert format_money_ascii(order.grand_total) in body


# ──────────────────────────────────────────────────────────────────────────────
# The endpoint
# ──────────────────────────────────────────────────────────────────────────────


def test_endpoint_serves_a_pdf(api_client, verified_user, paid_order) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    response = api_client.get(reverse("v1:orders:receipt", args=[paid_order.reference]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert paid_order.reference in response["Content-Disposition"]
    assert response.content.startswith(b"%PDF-")


def test_endpoint_refuses_an_unpaid_order(api_client, verified_user, ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    api_client.force_authenticate(verified_user)

    response = api_client.get(reverse("v1:orders:receipt", args=[order.reference]))

    assert response.status_code == 409
    assert response.json()["code"] == "order_not_paid"


def test_a_stranger_cannot_download_a_receipt(api_client, paid_order, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    intruder = User.objects.create_user(email="mal@example.com", password="x" * 20)
    api_client.force_authenticate(intruder)

    response = api_client.get(reverse("v1:orders:receipt", args=[paid_order.reference]))

    # 404, not 403: the existence of the reference is not disclosed.
    assert response.status_code == 404


def test_a_guest_can_download_with_their_token(api_client, ready_cart, branch) -> None:  # type: ignore[no-untyped-def]
    ready_cart.user = None
    ready_cart.save(update_fields=["user"])
    order = place_order(
        cart=ready_cart,
        payment_method="card",
        guest={"email": "guest@example.com", "phone": "+2348012345678"},
    )
    order.payment_status = PaymentStatus.PAID
    order.amount_paid = order.grand_total
    order.save(update_fields=["payment_status", "amount_paid"])

    response = api_client.get(
        reverse("v1:orders:receipt", args=[order.reference]),
        headers={"X-Guest-Token": order.guest_token},
    )
    assert response.status_code == 200

    denied = api_client.get(reverse("v1:orders:receipt", args=[order.reference]))
    assert denied.status_code == 404
