"""Rebuild a cart from a past order.

The frontend's version of this is `OrderHistorySection.tsx`, which pushes the
stored line objects straight back into the cart store — the *old* prices, dishes
that may have left the menu, options that may no longer exist. A reorder is not
a copy: it is a fresh quote for the same request, and the customer has to be
told what is different before they pay.

Three things can have changed since the order was placed, and each is reported
rather than silently applied:

* the price moved — the line is added at **today's** price and listed in ``changes``
* the dish, size or a required option is gone — the line is skipped and listed
  in ``unavailable``
* an optional extra is gone — the line is added without it and listed in ``changes``

Order lines are snapshots by design (see ``apps/orders/models.py``): they hold
the *name* of the variant and of each modifier, not a foreign key, because the
snapshot has to survive the catalogue row being deleted. Reorder therefore
re-resolves them by name against the current menu. A renamed option counts as a
removed one — which is the safe direction, since it is reported rather than
assumed equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from apps.carts.models import Cart, CartItem
from apps.carts.services.cart import add_item, clear
from apps.catalog.models import MenuItem, Modifier, Variant
from apps.common.exceptions import DomainError
from apps.common.money import format_money
from apps.orders.models import Order, OrderItem


class CartNotEmpty(DomainError):
    """The customer has a basket already, and reorder would overwrite it."""

    code = "cart_not_empty"
    title = "Your basket is not empty"
    status_code = 409


@dataclass
class ReorderResult:
    """What actually made it back into the basket, and what did not."""

    cart: Cart
    added: list[CartItem] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    unavailable: list[dict[str, Any]] = field(default_factory=list)
    replaced_lines: int = 0

    @property
    def is_complete(self) -> bool:
        return not self.unavailable

    @property
    def added_nothing(self) -> bool:
        return not self.added


def _resolve_item(line: OrderItem, cart: Cart) -> MenuItem | None:
    """Find the dish this line was for, if it is still orderable.

    Matched by foreign key first and by slug second: the key is nulled when a
    dish is deleted, but a dish that was deleted and recreated keeps its slug.
    """
    orderable = MenuItem.objects.orderable().filter(branch=cart.branch)
    if line.menu_item_id:
        found = orderable.filter(pk=line.menu_item_id).prefetch_related("modifier_groups").first()
        if found is not None:
            return found
    if line.slug_snapshot:
        return orderable.filter(slug=line.slug_snapshot).prefetch_related("modifier_groups").first()
    return None


def _resolve_variant(line: OrderItem, menu_item: MenuItem) -> tuple[Variant | None, bool]:
    """Return ``(variant, ok)``. ``ok`` is False when a named size has gone."""
    if not line.variant_name_snapshot:
        return None, True
    variant = Variant.objects.filter(
        item=menu_item, name=line.variant_name_snapshot, is_active=True
    ).first()
    return variant, variant is not None


def _resolve_modifiers(
    line: OrderItem, menu_item: MenuItem
) -> tuple[list[dict[str, Any]], list[str]]:
    """Re-resolve the chosen options by name. Returns ``(payload, dropped names)``."""
    payload: list[dict[str, Any]] = []
    dropped: list[str] = []
    for chosen in line.modifiers.all():
        modifier = Modifier.objects.filter(
            group__item=menu_item, name=chosen.name_snapshot, is_available=True
        ).first()
        if modifier is None:
            dropped.append(chosen.name_snapshot)
            continue
        payload.append({"modifier": str(modifier.id), "quantity": chosen.quantity})
    return payload, dropped


def _skip(line: OrderItem, reason: str) -> dict[str, Any]:
    return {
        "item": line.slug_snapshot,
        "name": line.name_snapshot,
        "reason": reason,
    }


@transaction.atomic
def reorder(*, order: Order, cart: Cart, replace: bool = False) -> ReorderResult:
    """Put a past order back in the basket, at today's prices.

    Refuses to run against a non-empty basket unless ``replace`` is passed. A
    reorder that silently discarded what the customer had already chosen would
    be destroying their work to save them a tap.
    """
    existing = cart.items.count()
    if existing and not replace:
        raise CartNotEmpty(
            "Reordering would replace the items already in your basket. "
            "Confirm to continue, or empty it first."
        )

    result = ReorderResult(cart=cart, replaced_lines=existing)
    if existing:
        clear(cart=cart)

    lines = order.items.prefetch_related("modifiers").select_related("menu_item")
    for line in lines:
        menu_item = _resolve_item(line, cart)
        if menu_item is None:
            result.unavailable.append(_skip(line, "This dish is no longer on the menu."))
            continue
        if not menu_item.available_at():
            result.unavailable.append(_skip(line, f"{menu_item.name} is unavailable right now."))
            continue

        variant, variant_ok = _resolve_variant(line, menu_item)
        if not variant_ok:
            result.unavailable.append(
                _skip(line, f"“{line.variant_name_snapshot}” is no longer offered.")
            )
            continue

        modifiers, dropped = _resolve_modifiers(line, menu_item)

        try:
            added = add_item(
                cart=cart,
                item_slug=menu_item.slug,
                quantity=line.quantity,
                variant_id=str(variant.id) if variant else None,
                modifiers=modifiers,
                special_instructions=line.special_instructions,
            )
        except DomainError as exc:
            # Most often a required option group that no longer has any
            # available choice. The line cannot be rebuilt as ordered.
            result.unavailable.append(_skip(line, str(exc)))
            continue

        result.added.append(added)

        if dropped:
            result.changes.append(
                {
                    "item": menu_item.slug,
                    "name": menu_item.name,
                    "type": "options_removed",
                    "detail": (
                        f"No longer available: {', '.join(dropped)}. "
                        "The item was added without them."
                    ),
                }
            )

        now = added.unit_price_snapshot
        if now != line.unit_price:
            result.changes.append(
                {
                    "item": menu_item.slug,
                    "name": menu_item.name,
                    "type": "price_increased" if now > line.unit_price else "price_reduced",
                    "old": {"amount": line.unit_price, "display": format_money(line.unit_price)},
                    "new": {"amount": now, "display": format_money(now)},
                }
            )

    return result
