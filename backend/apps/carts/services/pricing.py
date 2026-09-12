"""The pricing engine.

Every commercial term the frontend currently computes in the browser:

    const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;
    const tax = (subtotal - discount) * 0.075;
    const total = subtotal - discount + deliveryFee + tax;

...is computed here instead, in integer kobo, on the server, where a customer
cannot edit it.

Rules this module exists to enforce:

* All money is integer kobo. No binary floating point, anywhere.
* VAT is computed **per line by tax class** and then summed. Applying the rate
  to an order subtotal silently taxes zero-rated items.
* A discount is **allocated across lines** before VAT, using the
  largest-remainder method, so the parts sum exactly to the discount and each
  line's VAT is computed on what that line actually costs.
* Rounding happens once per component, never accumulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apps.catalog.models import TaxClass
from apps.common.money import allocate, format_money, vat_for


@dataclass(frozen=True, slots=True)
class PricedModifier:
    name: str
    price_delta: int
    quantity: int


@dataclass(frozen=True, slots=True)
class PricedLine:
    """One cart line, fully priced."""

    cart_item_id: str
    slug: str
    name: str
    variant_name: str
    quantity: int
    unit_price: int
    line_subtotal: int
    discount: int
    line_after_discount: int
    vat: int
    tax_class: str
    modifiers: list[PricedModifier]
    special_instructions: str
    image_url: str | None
    is_available: bool
    unavailable_reason: str
    price_changed: bool
    previous_unit_price: int | None


@dataclass(frozen=True, slots=True)
class PricedCart:
    """A fully priced cart. Everything the client needs, nothing it must compute."""

    lines: list[PricedLine]
    subtotal: int
    discount_total: int
    delivery_fee: int
    service_charge: int
    vat_total: int
    tip: int
    grand_total: int

    vat_rate_bps: int
    prices_include_vat: bool
    currency: str

    promo_code: str = ""
    delivery_note: str = ""
    vat_note: str = ""
    estimated_minutes: int | None = None

    changes: list[dict[str, Any]] = field(default_factory=list)
    unavailable: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[dict[str, str]] = field(default_factory=list)

    @property
    def can_checkout(self) -> bool:
        return not self.blockers


# ──────────────────────────────────────────────────────────────────────────────
# Line arithmetic (pure)
# ──────────────────────────────────────────────────────────────────────────────


def compute_unit_price(base_price: int, variant_delta: int, modifier_deltas: list[int]) -> int:
    """Unit price for a configured line.

    A variant delta may be negative (a smaller portion), so the result is
    floored at zero rather than allowed to go below it.
    """
    total = base_price + variant_delta + sum(modifier_deltas)
    return max(total, 0)


def compute_vat_for_lines(lines: list[tuple[int, str]], *, rate_bps: int, inclusive: bool) -> int:
    """Sum VAT across ``(amount, tax_class)`` pairs.

    Zero-rated and exempt lines contribute nothing. This is why VAT cannot be
    computed from an order subtotal: the subtotal has no tax class.
    """
    total = 0
    for amount, tax_class in lines:
        if tax_class != TaxClass.STANDARD:
            continue
        total += vat_for(amount, rate_bps, inclusive=inclusive)
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Cart pricing
# ──────────────────────────────────────────────────────────────────────────────


def price_cart(cart: Any) -> PricedCart:
    """Price a cart from live catalogue data.

    Called on every read, so a stale cart can never lock in a stale price.
    """
    from apps.carts.models import FulfilmentType
    from apps.promotions.services import calculate_discount, eligible_amount, validate_promo

    branch = cart.branch
    rate_bps = branch.vat_rate_bps
    inclusive = branch.prices_include_vat

    items = list(
        cart.items.select_related("menu_item__category", "variant").prefetch_related(
            "modifiers__modifier", "menu_item__images", "menu_item__availability_windows"
        )
    )

    # ── 1. Line subtotals from live prices ────────────────────────────────────
    raw_lines: list[dict[str, Any]] = []
    for item in items:
        menu_item = item.menu_item
        modifiers = [
            PricedModifier(
                name=link.modifier.name,
                price_delta=link.modifier.price_delta,
                quantity=link.quantity,
            )
            for link in item.modifiers.all()
        ]
        deltas = [modifier.price_delta * modifier.quantity for modifier in modifiers]
        variant_delta = item.variant.price_delta if item.variant else 0
        unit_price = compute_unit_price(menu_item.base_price, variant_delta, deltas)

        available = menu_item.available_at()
        reason = ""
        if not available:
            if not menu_item.is_orderable:
                reason = "withdrawn"
            elif not menu_item.is_available_now:
                reason = "sold_out"
            else:
                reason = "outside_serving_hours"

        primary = next((image for image in menu_item.images.all() if image.is_primary), None)
        image = primary or next(iter(menu_item.images.all()), None)

        raw_lines.append(
            {
                "item": item,
                "menu_item": menu_item,
                "unit_price": unit_price,
                "line_subtotal": unit_price * item.quantity,
                "modifiers": modifiers,
                "available": available,
                "reason": reason,
                "image_url": image.image.url if image and image.image else None,
            }
        )

    subtotal = sum(line["line_subtotal"] for line in raw_lines)

    # ── 2. Promo ──────────────────────────────────────────────────────────────
    discount_total = 0
    free_delivery = False
    promo_code_label = ""
    promo = cart.promo_code

    if promo is not None:

        class _Line:
            __slots__ = ("line_subtotal", "menu_item")

            def __init__(self, subtotal_: int, menu_item: Any) -> None:
                self.line_subtotal = subtotal_
                self.menu_item = menu_item

        candidate_lines = [_Line(line["line_subtotal"], line["menu_item"]) for line in raw_lines]
        eligible = eligible_amount(promo, candidate_lines)
        check = validate_promo(
            promo=promo, subtotal=subtotal, user=cart.user, eligible_subtotal=eligible
        )
        if check.ok:
            promo_code_label = promo.code
            discount_total = calculate_discount(promo, eligible)
            free_delivery = promo.discount_type == "free_delivery"

    # ── 3. Allocate the discount across lines, before VAT ─────────────────────
    weights = [line["line_subtotal"] for line in raw_lines]
    if discount_total and any(weights):
        allocations = allocate(discount_total, weights)
    else:
        allocations = [0] * len(raw_lines)

    # ── 4. Delivery ───────────────────────────────────────────────────────────
    delivery_fee = 0
    delivery_note = ""
    estimated_minutes: int | None = None
    blockers: list[dict[str, str]] = []

    if cart.fulfilment_type == FulfilmentType.DELIVERY:
        address = cart.delivery_address
        zone = address.zone if address else None
        if address is None:
            blockers.append(
                {"code": "address_required", "detail": "Choose a delivery address to continue."}
            )
        elif zone is None:
            blockers.append(
                {
                    "code": "outside_delivery_area",
                    "detail": "We do not deliver to that address yet. Pickup is available.",
                }
            )
        else:
            estimated_minutes = zone.estimated_minutes
            threshold = branch.free_delivery_threshold
            if free_delivery:
                delivery_note = f"Free delivery applied with {promo_code_label}."
            elif threshold is not None and subtotal >= threshold:
                delivery_note = f"Free delivery — order over {format_money(threshold)}."
            else:
                delivery_fee = zone.fee
                delivery_note = f"Delivery to {zone.name}."

            if subtotal < zone.min_order_value:
                blockers.append(
                    {
                        "code": "below_minimum_order",
                        "detail": (
                            f"Orders to {zone.name} start at {format_money(zone.min_order_value)}."
                        ),
                    }
                )
    else:
        delivery_note = "Collection from the restaurant."
        estimated_minutes = max(
            (line["menu_item"].effective_prep_minutes for line in raw_lines), default=None
        )

    # ── 5. Service charge ─────────────────────────────────────────────────────
    from apps.common.money import apply_bps

    net_goods = subtotal - discount_total
    service_charge = apply_bps(max(net_goods, 0), branch.service_charge_bps)

    # ── 6. VAT, per line by tax class ─────────────────────────────────────────
    vat_inputs: list[tuple[int, str]] = []
    priced_lines: list[PricedLine] = []
    changes: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []

    for line, allocated in zip(raw_lines, allocations, strict=True):
        item = line["item"]
        menu_item = line["menu_item"]
        after_discount = line["line_subtotal"] - allocated
        line_vat = (
            vat_for(after_discount, rate_bps, inclusive=inclusive)
            if menu_item.tax_class == TaxClass.STANDARD
            else 0
        )
        vat_inputs.append((after_discount, menu_item.tax_class))

        snapshot = item.unit_price_snapshot
        price_changed = bool(snapshot) and snapshot != line["unit_price"]
        if price_changed:
            changes.append(
                {
                    "item": menu_item.slug,
                    "name": menu_item.name,
                    "type": "price_increased" if line["unit_price"] > snapshot else "price_reduced",
                    "old": {"amount": snapshot, "display": format_money(snapshot)},
                    "new": {
                        "amount": line["unit_price"],
                        "display": format_money(line["unit_price"]),
                    },
                }
            )
        if not line["available"]:
            unavailable.append(
                {"item": menu_item.slug, "name": menu_item.name, "reason": line["reason"]}
            )

        priced_lines.append(
            PricedLine(
                cart_item_id=str(item.pk),
                slug=menu_item.slug,
                name=menu_item.name,
                variant_name=item.variant.name if item.variant else "",
                quantity=item.quantity,
                unit_price=line["unit_price"],
                line_subtotal=line["line_subtotal"],
                discount=allocated,
                line_after_discount=after_discount,
                vat=line_vat,
                tax_class=menu_item.tax_class,
                modifiers=line["modifiers"],
                special_instructions=item.special_instructions,
                image_url=line["image_url"],
                is_available=line["available"],
                unavailable_reason=line["reason"],
                price_changed=price_changed,
                previous_unit_price=snapshot if price_changed else None,
            )
        )

    # Delivery and service charge are standard-rated.
    vat_inputs.append((delivery_fee, TaxClass.STANDARD))
    vat_inputs.append((service_charge, TaxClass.STANDARD))
    vat_total = compute_vat_for_lines(vat_inputs, rate_bps=rate_bps, inclusive=inclusive)

    # ── 7. Grand total ────────────────────────────────────────────────────────
    tip = cart.tip
    if inclusive:
        # VAT already sits inside the prices shown, so it is not added again.
        grand_total = net_goods + delivery_fee + service_charge + tip
        vat_note = f"VAT of {format_money(vat_total)} is included in the prices shown."
    else:
        grand_total = net_goods + delivery_fee + service_charge + vat_total + tip
        vat_note = f"VAT of {format_money(vat_total)} is added at checkout."

    if unavailable:
        blockers.append(
            {
                "code": "item_unavailable",
                "detail": "Remove the unavailable items to continue.",
            }
        )
    if not raw_lines:
        blockers.append({"code": "cart_empty", "detail": "Your cart is empty."})
    if not branch.can_accept_orders:
        blockers.append(
            {"code": "branch_closed", "detail": "We are not accepting orders right now."}
        )
    if raw_lines and subtotal < branch.min_order_value:
        blockers.append(
            {
                "code": "below_minimum_order",
                "detail": f"Minimum order is {format_money(branch.min_order_value)}.",
            }
        )

    return PricedCart(
        lines=priced_lines,
        subtotal=subtotal,
        discount_total=discount_total,
        delivery_fee=delivery_fee,
        service_charge=service_charge,
        vat_total=vat_total,
        tip=tip,
        grand_total=max(grand_total, 0),
        vat_rate_bps=rate_bps,
        prices_include_vat=inclusive,
        currency=branch.currency,
        promo_code=promo_code_label,
        delivery_note=delivery_note,
        vat_note=vat_note,
        estimated_minutes=estimated_minutes,
        changes=changes,
        unavailable=unavailable,
        blockers=blockers,
    )
