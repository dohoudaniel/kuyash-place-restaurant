"""Cart mutation services."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.carts.models import Cart, CartItem, CartItemModifier, CartStatus, FulfilmentType
from apps.catalog.models import MenuItem, Modifier, Variant
from apps.common.exceptions import DomainError, ItemUnavailable, PromoInvalid


class CartValidationError(DomainError):
    code = "cart_invalid"
    title = "That cannot be added to your cart"
    status_code = 422


def resolve_cart(*, branch: Any, user: Any = None, session_token: str = "") -> Cart:
    """Find or create the caller's active cart.

    A signed-in user gets their user cart; an anonymous caller gets the cart
    matching their ``X-Cart-Token``.
    """
    if user is not None and getattr(user, "is_authenticated", False):
        cart = Cart.objects.filter(user=user, branch=branch, status=CartStatus.ACTIVE).first()
        if cart is None:
            cart = Cart.objects.create(user=user, branch=branch)
        return cart

    if session_token:
        cart = Cart.objects.filter(
            session_token=session_token, branch=branch, status=CartStatus.ACTIVE, user__isnull=True
        ).first()
        if cart is not None:
            return cart
    return Cart.objects.create(branch=branch)


def _validate_modifier_selection(
    menu_item: MenuItem, selections: list[dict[str, Any]]
) -> list[tuple[Modifier, int]]:
    """Check a modifier selection against the item's own groups.

    The frontend validates against one global ``MOCK_CUSTOMIZATIONS`` array, so
    its "Please select all required options" gate is meaningless — and the
    selections it does collect carry no price.
    """
    by_id = {
        str(selection["modifier"]): int(selection.get("quantity", 1)) for selection in selections
    }

    modifiers = list(Modifier.objects.filter(id__in=by_id.keys()).select_related("group__item"))
    found = {str(modifier.id) for modifier in modifiers}
    missing = set(by_id) - found
    if missing:
        raise CartValidationError("One or more selected options do not exist.")

    for modifier in modifiers:
        if modifier.group.item_id != menu_item.id:
            raise CartValidationError(f"“{modifier.name}” is not an option for {menu_item.name}.")
        if not modifier.is_available:
            raise ItemUnavailable(f"“{modifier.name}” is unavailable right now.")

    chosen_per_group: dict[Any, int] = {}
    for modifier in modifiers:
        chosen_per_group[modifier.group_id] = chosen_per_group.get(modifier.group_id, 0) + 1

    for group in menu_item.modifier_groups.all():
        count = chosen_per_group.get(group.id, 0)
        if count < group.min_select:
            raise CartValidationError(
                f"Choose at least {group.min_select} option(s) for “{group.name}”."
            )
        if count > group.max_select:
            raise CartValidationError(
                f"Choose at most {group.max_select} option(s) for “{group.name}”."
            )

    return [(modifier, max(by_id[str(modifier.id)], 1)) for modifier in modifiers]


@transaction.atomic
def add_item(
    *,
    cart: Cart,
    item_slug: str,
    quantity: int = 1,
    variant_id: str | None = None,
    modifiers: list[dict[str, Any]] | None = None,
    special_instructions: str = "",
) -> CartItem:
    """Add a configured line.

    Any ``price`` in the payload is ignored — the price comes from the
    catalogue, every time.
    """
    if quantity < 1:
        raise CartValidationError("Quantity must be at least 1.")

    menu_item = (
        MenuItem.objects.orderable()
        .filter(branch=cart.branch, slug=item_slug)
        .prefetch_related("modifier_groups")
        .first()
    )
    if menu_item is None:
        raise ItemUnavailable("That item is not on the menu.")
    if not menu_item.available_at():
        raise ItemUnavailable(f"{menu_item.name} is unavailable right now.")

    variant = None
    if variant_id:
        variant = Variant.objects.filter(id=variant_id, item=menu_item, is_active=True).first()
        if variant is None:
            raise CartValidationError("That size or portion is not available for this item.")

    selected = _validate_modifier_selection(menu_item, modifiers or [])

    deltas = [modifier.price_delta * count for modifier, count in selected]
    from apps.carts.services.pricing import compute_unit_price

    unit_price = compute_unit_price(
        menu_item.base_price, variant.price_delta if variant else 0, deltas
    )

    line = CartItem.objects.create(
        cart=cart,
        menu_item=menu_item,
        variant=variant,
        quantity=quantity,
        special_instructions=special_instructions.strip(),
        unit_price_snapshot=unit_price,
    )
    for modifier, count in selected:
        CartItemModifier.objects.create(cart_item=line, modifier=modifier, quantity=count)

    cart.save(update_fields=["expires_at", "updated_at"])
    return line


@transaction.atomic
def update_item(
    *, item: CartItem, quantity: int | None = None, instructions: str | None = None
) -> CartItem:
    if quantity is not None:
        if quantity < 1:
            raise CartValidationError("Quantity must be at least 1. Remove the line instead.")
        item.quantity = quantity
    if instructions is not None:
        item.special_instructions = instructions.strip()
    item.save()
    return item


@transaction.atomic
def merge_carts(*, guest_cart: Cart, user_cart: Cart) -> Cart:
    """Fold an anonymous cart into the signed-in one on login.

    Lines are moved rather than merged by product: two lines of the same dish
    with different options are genuinely different lines.
    """
    if guest_cart.pk == user_cart.pk:
        return user_cart

    guest_cart.items.update(cart=user_cart)
    if user_cart.promo_code is None and guest_cart.promo_code is not None:
        user_cart.promo_code = guest_cart.promo_code
    if not user_cart.tip and guest_cart.tip:
        user_cart.tip = guest_cart.tip
    user_cart.save()

    guest_cart.status = CartStatus.ABANDONED
    guest_cart.save(update_fields=["status", "updated_at"])
    return user_cart


@transaction.atomic
def apply_promo(*, cart: Cart, code: str) -> Cart:
    """Validate and attach a promo code.

    Validation happens against the live cart, so a code cannot be attached and
    then have its conditions quietly stop holding.
    """
    from apps.carts.services.pricing import price_cart
    from apps.promotions.services import eligible_amount, find_code, validate_promo

    promo = find_code(cart.branch, code)
    priced = price_cart(cart)

    class _Line:
        __slots__ = ("line_subtotal", "menu_item")

        def __init__(self, subtotal: int, menu_item: Any) -> None:
            self.line_subtotal = subtotal
            self.menu_item = menu_item

    lines = [
        _Line(line.line_subtotal, item.menu_item)
        for line, item in zip(priced.lines, cart.items.select_related("menu_item"), strict=False)
    ]
    eligible = eligible_amount(promo, lines) if promo else 0

    check = validate_promo(
        promo=promo, subtotal=priced.subtotal, user=cart.user, eligible_subtotal=eligible
    )
    if not check.ok:
        raise PromoInvalid(check.reason)

    cart.promo_code = promo
    cart.save(update_fields=["promo_code", "updated_at"])
    return cart


def remove_promo(*, cart: Cart) -> Cart:
    cart.promo_code = None
    cart.save(update_fields=["promo_code", "updated_at"])
    return cart


@transaction.atomic
def set_fulfilment(
    *,
    cart: Cart,
    fulfilment_type: str | None = None,
    address_id: str | None = None,
    tip: int | None = None,
) -> Cart:
    """Set delivery/pickup, the address and the tip."""
    from apps.accounts.models import Address

    if fulfilment_type is not None:
        if fulfilment_type not in FulfilmentType.values:
            raise CartValidationError("Choose either delivery or pickup.")
        cart.fulfilment_type = fulfilment_type
        if fulfilment_type == FulfilmentType.PICKUP:
            cart.delivery_address = None

    if address_id is not None:
        if cart.user is None:
            raise CartValidationError("Sign in to use a saved address.")
        address = Address.objects.filter(id=address_id, user=cart.user).first()
        if address is None:
            raise CartValidationError("That address does not exist.")
        cart.delivery_address = address
        cart.fulfilment_type = FulfilmentType.DELIVERY

    if tip is not None:
        if tip < 0:
            raise CartValidationError("A tip cannot be negative.")
        cart.tip = tip

    cart.save()
    return cart


def clear(*, cart: Cart) -> Cart:
    cart.items.all().delete()
    cart.promo_code = None
    cart.tip = 0
    cart.save()
    return cart
