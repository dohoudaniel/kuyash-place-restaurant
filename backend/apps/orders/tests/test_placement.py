"""Order placement.

Replaces `app/checkout/page.tsx`, which generates an id from Date.now(),
clears the cart, and persists nothing.
"""

from __future__ import annotations

import pytest

from apps.carts.models import CartStatus
from apps.common.exceptions import BranchClosed, ItemUnavailable, PriceChanged
from apps.orders.models import Order, OrderStatus, PaymentStatus
from apps.orders.services.placement import CheckoutBlocked, place_order
from apps.orders.services.state import transition
from apps.payments.models import PaymentTransaction, Provider, TransactionStatus
from apps.promotions.models import PromoRedemption, RedemptionStatus

pytestmark = pytest.mark.django_db


def place(cart, **kwargs):  # type: ignore[no-untyped-def]
    return place_order(cart=cart, payment_method=kwargs.pop("payment_method", "card"), **kwargs)


def test_placing_an_order_snapshots_the_lines(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    line = order.items.get()
    assert line.name_snapshot == "Classic Smash Burger"
    assert line.unit_price == 1_090_000
    assert line.quantity == 2
    assert order.subtotal == 2_180_000


def test_the_snapshot_survives_a_later_price_change(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Raising a price must not rewrite what a customer already agreed to pay."""
    from apps.catalog.models import MenuItem

    order = place(ready_cart)
    original = order.grand_total

    item = MenuItem.objects.get(slug="classic-smash-burger")
    item.base_price = 9_999_000
    item.save()

    order.refresh_from_db()
    assert order.grand_total == original
    assert order.items.get().unit_price == 1_090_000


def test_the_address_is_copied_not_referenced(ready_cart, address) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    assert order.street == "12 Adeola Odeku Street"
    assert order.delivery_zone_name == "Victoria Island"

    address.street = "Somewhere else entirely"
    address.save()
    order.refresh_from_db()
    assert order.street == "12 Adeola Odeku Street"


def test_references_are_random_and_unique(ready_cart, branch, category) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.models import generate_reference

    references = {generate_reference() for _ in range(500)}
    assert len(references) == 500
    assert all(ref.startswith("KYS-") and len(ref) == 10 for ref in references)
    # No ambiguous characters: an order reference gets read aloud on the phone.
    assert not any(set("01OI") & set(ref[4:]) for ref in references)


def test_card_orders_await_payment(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart, payment_method="card")
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.payment_status == PaymentStatus.PENDING


def test_cash_orders_are_confirmed_immediately(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart, payment_method="cash")
    assert order.status == OrderStatus.CONFIRMED
    assert order.payment_status == PaymentStatus.UNPAID


def test_the_cart_is_not_cleared_until_payment(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """ORD-4. The frontend clears the cart before anything is persisted, so a
    failed payment loses the basket with no way back."""
    order = place(ready_cart)
    ready_cart.refresh_from_db()
    assert ready_cart.status == CartStatus.CONVERTED
    assert ready_cart.items.exists()  # still there

    transition(order, OrderStatus.PAID)
    ready_cart.refresh_from_db()
    assert not ready_cart.items.exists()  # cleared only now


def test_the_price_changed_guard_refuses_a_mismatch(ready_cart) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PriceChanged) as excinfo:
        place(ready_cart, expected_total=1)
    assert excinfo.value.extra["actual"]["amount"] == 2_180_000
    assert not Order.objects.exists()


def test_a_matching_expected_total_is_accepted(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.carts.services.pricing import price_cart

    total = price_cart(ready_cart).grand_total
    assert place(ready_cart, expected_total=total).grand_total == total


def test_an_empty_cart_cannot_be_ordered(user_cart, address) -> None:  # type: ignore[no-untyped-def]
    user_cart.delivery_address = address
    user_cart.save()
    with pytest.raises(CheckoutBlocked, match="empty"):
        place(user_cart)


def test_a_sold_out_item_blocks_placement(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.catalog.models import MenuItem

    item = MenuItem.objects.get(slug="classic-smash-burger")
    item.is_available_now = False
    item.save()

    with pytest.raises(ItemUnavailable):
        place(ready_cart)
    assert not Order.objects.exists()


def test_a_closed_branch_blocks_placement(ready_cart, branch) -> None:  # type: ignore[no-untyped-def]
    branch.is_accepting_orders = False
    branch.save()
    with pytest.raises(BranchClosed):
        place(ready_cart)


def test_an_undeliverable_address_blocks_placement(ready_cart, verified_user) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import Address

    ready_cart.delivery_address = Address.objects.create(
        user=verified_user,
        label="other",
        recipient_name="Ada",
        phone="+2348012345678",
        street="5 Aso Drive",
        area="Maitama",
        city="Abuja",
        state="FCT",
    )
    ready_cart.save()
    with pytest.raises(CheckoutBlocked):
        place(ready_cart)


def test_a_guest_order_requires_an_email(branch, category, cart, zone) -> None:  # type: ignore[no-untyped-def]
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

    with pytest.raises(CheckoutBlocked, match="email"):
        place(cart)

    order = place(cart, guest={"email": "guest@example.com", "phone": "+2348012345678"})
    assert order.guest_email == "guest@example.com"
    assert order.guest_token


def test_an_eta_is_calculated(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    assert order.estimated_ready_at is not None
    assert order.estimated_delivery_at > order.estimated_ready_at


def test_a_promo_creates_a_pending_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)

    redemption = PromoRedemption.objects.get(order=order)
    assert redemption.status == RedemptionStatus.PENDING
    assert redemption.discount_amount == order.discount_total
    assert order.promo_code_snapshot == "WELCOME10"


def test_payment_confirms_the_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)

    transition(order, OrderStatus.PAID)
    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.CONFIRMED


def test_cancelling_reverses_the_redemption(ready_cart, promo) -> None:  # type: ignore[no-untyped-def]
    """RF-4: a customer gets their promo use back."""
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)
    transition(order, OrderStatus.PAID)

    transition(order, OrderStatus.CANCELLED)
    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.REVERSED
    assert promo.times_used == 0  # the allowance is free again


def test_payment_queues_a_confirmation_email(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.notifications.models import Notification

    order = place(ready_cart)
    transition(order, OrderStatus.PAID)
    assert Notification.objects.filter(
        template_key="order_confirmation", recipient="ada@example.com"
    ).exists()


def test_delivery_increments_popularity(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """So "sort by popular" reflects real sales rather than a placeholder."""
    from apps.catalog.models import MenuItem

    order = place(ready_cart)
    for status in (
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ):
        transition(order, status)

    assert MenuItem.objects.get(slug="classic-smash-burger").order_count == 2


def test_payment_marks_the_amount_paid(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    transition(order, OrderStatus.PAID)
    order.refresh_from_db()
    assert order.payment_status == PaymentStatus.PAID
    assert order.amount_paid == order.grand_total


def test_a_transfer_order_is_refused_when_there_is_no_account_to_pay_into(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Hiding the option is not enough: the API itself refuses."""
    from apps.orders.services.placement import CheckoutBlocked

    with pytest.raises(CheckoutBlocked):
        place(ready_cart, payment_method="transfer")


def test_a_transfer_order_is_accepted_once_bank_details_exist(ready_cart) -> None:  # type: ignore[no-untyped-def]
    branch = ready_cart.branch
    branch.bank_name = "Example Bank"
    branch.bank_account_name = "Kuyash Place Ltd"
    branch.bank_account_number = "0123456789"
    branch.save()

    order = place(ready_cart, payment_method="transfer")

    assert order.payment_method == "transfer"
    assert order.status == "pending_payment"


# ── Whose basket gets cleared ─────────────────────────────────────────────────


def test_payment_clears_only_the_basket_that_order_came_from(ready_cart, cart) -> None:  # type: ignore[no-untyped-def]
    """A guest sitting on the payment page keeps their items when someone else pays.

    The receiver used to find carts by customer identity and branch rather than
    by the order's own cart, so it emptied every converted basket that matched.
    """
    from apps.carts.services import cart as svc

    svc.add_item(cart=cart, item_slug="classic-smash-burger")
    cart.status = CartStatus.CONVERTED
    cart.save(update_fields=["status", "updated_at"])

    transition(place(ready_cart), OrderStatus.PAID)

    ready_cart.refresh_from_db()
    assert not ready_cart.items.exists()
    assert cart.items.exists(), "another customer's basket was emptied"


def test_paying_one_order_leaves_the_customers_other_basket_alone(  # type: ignore[no-untyped-def]
    ready_cart, verified_user, branch, address
) -> None:
    """A customer with two outstanding orders keeps the unpaid one's basket."""
    from apps.carts.models import Cart
    from apps.carts.services import cart as svc

    unpaid = place(ready_cart)

    second = Cart.objects.create(branch=branch, user=verified_user)
    svc.add_item(cart=second, item_slug="classic-smash-burger", quantity=2)
    second.delivery_address = address
    second.save()

    transition(place(second), OrderStatus.PAID)

    ready_cart.refresh_from_db()
    assert not second.items.exists()
    assert ready_cart.items.exists(), "the unpaid order's basket was emptied"
    assert unpaid.status == OrderStatus.PENDING_PAYMENT


# ── What was actually received ────────────────────────────────────────────────


def settle(order, suffix: str, *, verified: int, status: str = TransactionStatus.SUCCESS):  # type: ignore[no-untyped-def]
    return PaymentTransaction.objects.create(
        order=order,
        provider=Provider.PAYSTACK,
        our_reference=f"{order.reference}-{suffix}",
        amount=order.grand_total,
        amount_verified=verified,
        currency=order.currency,
        status=status,
    )


def test_amount_paid_sums_every_settled_transaction(ready_cart) -> None:  # type: ignore[no-untyped-def]
    """Two tabs produce two live checkout URLs and two charges.

    ``amount_paid`` used to be the order total regardless, and refunds are
    capped at it — so the second charge could not be refunded through the API.
    """
    order = place(ready_cart)
    settle(order, "a", verified=order.grand_total)
    settle(order, "b", verified=order.grand_total)

    transition(order, OrderStatus.PAID)

    order.refresh_from_db()
    assert order.amount_paid == order.grand_total * 2


def test_amount_paid_ignores_a_transaction_that_never_settled(ready_cart) -> None:  # type: ignore[no-untyped-def]
    order = place(ready_cart)
    settle(order, "failed", verified=500_000, status=TransactionStatus.FAILED)

    transition(order, OrderStatus.PAID)

    order.refresh_from_db()
    # Nothing settled, so there is nothing to derive from and the total stands.
    assert order.amount_paid == order.grand_total


# ── The promo ledger ──────────────────────────────────────────────────────────


def free_delivery_code(branch, **kwargs):  # type: ignore[no-untyped-def]
    from apps.promotions.models import DiscountType, PromoCode

    return PromoCode.objects.create(
        branch=branch, code="FREESHIP", discount_type=DiscountType.FREE_DELIVERY, **kwargs
    )


def test_a_free_delivery_code_is_written_to_the_ledger(ready_cart, branch) -> None:  # type: ignore[no-untyped-def]
    """It takes nothing off the goods, so it used to be recorded nowhere at all —
    and ``times_used`` is derived purely from this ledger."""
    code = free_delivery_code(branch, usage_limit=1)
    ready_cart.promo_code = code
    ready_cart.save()

    order = place(ready_cart)

    redemption = PromoRedemption.objects.get(order=order)
    assert redemption.discount_amount == 0
    assert redemption.status == RedemptionStatus.PENDING
    assert code.times_used == 1


def test_a_free_delivery_codes_usage_limit_is_enforceable(  # type: ignore[no-untyped-def]
    ready_cart, branch, verified_user, address
) -> None:
    """Infinite-use, by everyone, forever, with no audit trail, was the old behaviour."""
    from apps.carts.models import Cart
    from apps.carts.services import cart as svc

    code = free_delivery_code(branch, usage_limit=1)
    ready_cart.promo_code = code
    ready_cart.save()
    first = place(ready_cart)
    assert first.promo_code_snapshot == "FREESHIP"

    second_cart = Cart.objects.create(branch=branch, user=verified_user)
    svc.add_item(cart=second_cart, item_slug="classic-smash-burger", quantity=2)
    second_cart.delivery_address = address
    second_cart.promo_code = code
    second_cart.save()

    second = place(second_cart)

    # One redemption, and the second order does not carry the code at all.
    assert PromoRedemption.objects.filter(promo_code=code).count() == 1
    assert second.promo_code_snapshot == "", "the code was honoured past its usage limit"


@pytest.mark.parametrize("abandoned", [OrderStatus.EXPIRED, OrderStatus.FAILED])
def test_abandoning_payment_gives_the_promo_use_back(ready_cart, promo, abandoned) -> None:  # type: ignore[no-untyped-def]
    """Loyalty already reversed points on both of these and the promo ledger did
    not, so the two ledgers disagreed about the same event: walking away from
    the provider's page permanently burned a one-per-customer code."""
    ready_cart.promo_code = promo
    ready_cart.save()
    order = place(ready_cart)

    transition(order, abandoned)

    assert PromoRedemption.objects.get(order=order).status == RedemptionStatus.REVERSED
    assert promo.times_used == 0


def test_placement_rechecks_a_promo_after_claiming_it(ready_cart, branch, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The cart priced while the last use was free; another checkout took it a
    moment later. Re-reading the limit under the row lock is what catches that —
    it used to be read once, before anything was written."""
    from apps.common.exceptions import PromoInvalid
    from apps.promotions.models import DiscountType, PromoCode

    code = PromoCode.objects.create(
        branch=branch,
        code="LASTONE",
        discount_type=DiscountType.FIXED,
        value=100_000,
        usage_limit=1,
    )
    ready_cart.promo_code = code
    ready_cart.save()

    reads = {"count": 0}

    def times_used(self) -> int:  # type: ignore[no-untyped-def]
        reads["count"] += 1
        return 0 if reads["count"] == 1 else 1

    monkeypatch.setattr(PromoCode, "times_used", property(times_used))

    with pytest.raises(PromoInvalid, match="fully redeemed"):
        place(ready_cart)
    assert not Order.objects.exists()


def test_placement_does_not_cost_a_query_per_line(branch, category) -> None:  # type: ignore[no-untyped-def]
    """Around forty INSERTs where two bulk_creates do, on the single most
    important path in the system."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from apps.carts.models import Cart, FulfilmentType
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem

    for slug in ("one", "two", "three"):
        MenuItem.objects.create(
            branch=branch,
            category=category,
            name=slug,
            slug=slug,
            base_price=1_000_000,
            needs_repricing=False,
        )

    def basket(slugs: list[str]) -> Cart:
        created = Cart.objects.create(branch=branch)
        for slug in slugs:
            svc.add_item(cart=created, item_slug=slug)
        created.fulfilment_type = FulfilmentType.PICKUP
        created.save()
        return created

    guest = {"email": "guest@example.com", "phone": "+2348012345678"}
    one_line, three_lines = basket(["one"]), basket(["one", "two", "three"])

    with CaptureQueriesContext(connection) as small:
        place(one_line, guest=guest)
    with CaptureQueriesContext(connection) as large:
        place(three_lines, guest=guest)

    assert len(large) == len(small), "the line snapshots cost a query each"
