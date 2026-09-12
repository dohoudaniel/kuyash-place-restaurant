"""PDF receipts.

A receipt is a financial document, so this module is deliberately dull: it
prints the values already snapshotted on the order and computes nothing. The
order carries the rate that applied at the time (``vat_rate_bps``) and whether
prices included VAT then (``prices_included_vat``); re-deriving either from
today's branch settings would reprint history as whatever the current
configuration happens to be.

Money is rendered with :func:`format_money_ascii`, not the naira sign. The
standard PDF fonts use WinAnsiEncoding, which has no U+20A6, and reportlab
substitutes it silently — a receipt reading ``n3,312.00`` is worse than one
reading ``NGN 3,312.00``.
"""

from __future__ import annotations

import io
from typing import Any

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.common.exceptions import DomainError
from apps.common.money import format_money_ascii
from apps.orders.models import Order

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 20 * mm
RIGHT = PAGE_WIDTH - 20 * mm
BODY = 9.5
SMALL = 8


class OrderNotPaid(DomainError):
    """No money received, so there is nothing to receipt."""

    code = "order_not_paid"
    title = "This order has not been paid"
    status_code = 409


class _Sheet:
    """A cursor that walks down the page and starts a new one when it runs out."""

    def __init__(self, pdf: canvas.Canvas) -> None:
        self.pdf = pdf
        self.y = PAGE_HEIGHT - 20 * mm

    def _ensure(self, needed: float) -> None:
        if self.y - needed < 20 * mm:
            self.pdf.showPage()
            self.y = PAGE_HEIGHT - 20 * mm

    def line(
        self, text: str, *, size: float = BODY, bold: bool = False, gap: float = 5 * mm
    ) -> None:
        self._ensure(gap)
        self.pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.pdf.drawString(LEFT, self.y, text)
        self.y -= gap

    def row(self, left: str, right: str, *, bold: bool = False, size: float = BODY) -> None:
        self._ensure(5 * mm)
        self.pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.pdf.drawString(LEFT, self.y, left)
        self.pdf.drawRightString(RIGHT, self.y, right)
        self.y -= 5 * mm

    def rule(self) -> None:
        self._ensure(4 * mm)
        self.pdf.setLineWidth(0.4)
        self.pdf.line(LEFT, self.y + 1.5 * mm, RIGHT, self.y + 1.5 * mm)
        self.y -= 4 * mm

    def gap(self, amount: float = 3 * mm) -> None:
        self.y -= amount


def _address_lines(order: Order) -> list[str]:
    parts = [order.street, order.area, order.city, order.state]
    return [part for part in parts if part]


def _tax_note(order: Order) -> str:
    rate = order.vat_rate_bps / 100
    if order.prices_included_vat:
        return f"Item prices include VAT at {rate:g}%. VAT shown is the portion contained in them."
    return f"VAT at {rate:g}% was added to the item prices shown."


def render_receipt_pdf(order: Order) -> bytes:
    """Render a receipt for a paid order.

    Refuses an unpaid one. A document headed "Receipt" for money that was never
    received is exactly what causes the dispute it is meant to settle — a cash
    order becomes receiptable when the rider marks it paid, not when it is
    placed.
    """
    if not order.is_paid:
        raise OrderNotPaid("A receipt is available once this order has been paid for.")

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Receipt {order.reference}")
    pdf.setAuthor(order.branch.name)
    sheet = _Sheet(pdf)

    branch = order.branch
    sheet.line(branch.name, size=15, bold=True, gap=7 * mm)
    for detail in (branch.address_line, f"{branch.city}, {branch.state}".strip(", "), branch.phone):
        if detail:
            sheet.line(detail, size=SMALL, gap=4 * mm)
    sheet.gap()
    sheet.rule()

    sheet.line("RECEIPT", size=12, bold=True, gap=6 * mm)
    issued = timezone.localtime(order.placed_at or order.created_at)
    sheet.row("Order", order.reference)
    sheet.row("Date", issued.strftime("%d %b %Y, %H:%M"))
    sheet.row("Customer", order.contact_name or "—")
    # `fulfilment_type` has no choices on the model, so there is no
    # get_..._display() to call.
    sheet.row("Fulfilment", order.fulfilment_type.replace("_", " ").title())
    if lines := _address_lines(order):
        sheet.row("Delivery to", ", ".join(lines))
    sheet.gap()
    sheet.rule()

    sheet.row("Item", "Amount", bold=True)
    for item in order.items.all():
        label = f"{item.quantity}x {item.name_snapshot}"
        if item.variant_name_snapshot:
            label += f" ({item.variant_name_snapshot})"
        sheet.row(label, format_money_ascii(item.line_subtotal, order.currency))
        for modifier in item.modifiers.all():
            delta = format_money_ascii(modifier.price_delta, order.currency)
            sheet.line(f"     + {modifier.name_snapshot}  {delta}", size=SMALL, gap=4 * mm)
        if item.special_instructions:
            sheet.line(f"     Note: {item.special_instructions}", size=SMALL, gap=4 * mm)
    sheet.gap()
    sheet.rule()

    def money(amount: int) -> str:
        return format_money_ascii(amount, order.currency)

    sheet.row("Subtotal", money(order.subtotal))
    if order.discount_total:
        label = "Discount"
        if order.promo_code_snapshot:
            label += f" ({order.promo_code_snapshot})"
        sheet.row(label, f"-{money(order.discount_total)}")
    if order.delivery_fee:
        sheet.row("Delivery", money(order.delivery_fee))
    if order.service_charge:
        sheet.row("Service charge", money(order.service_charge))
    if order.tip:
        sheet.row("Tip", money(order.tip))
    sheet.row("VAT", money(order.vat_total))
    sheet.rule()
    sheet.row("Total", money(order.grand_total), bold=True, size=11)
    sheet.gap()

    sheet.row("Paid", money(order.amount_paid))
    sheet.row("Method", order.get_payment_method_display())
    sheet.gap()
    sheet.line(_tax_note(order), size=SMALL, gap=4 * mm)
    sheet.line("Thank you for your order.", size=SMALL, gap=4 * mm)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


__all__: list[Any] = ["OrderNotPaid", "render_receipt_pdf"]
