"""Correctness under concurrency.

Locust measures throughput; these measure that concurrency cannot corrupt
state. They are the half that actually matters for money, and they run in CI.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections

from apps.common import idempotency
from apps.common.exceptions import IdempotencyConflict, IdempotencyKeyReuse, IllegalTransition
from apps.orders.models import Order, OrderStatus, OrderStatusEvent
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


def test_one_idempotency_key_admits_one_request() -> None:
    """The second holder of a key in flight is refused, not queued.

    This is what stops a double-tapped Confirm button taking two payments.
    """
    key = str(uuid.uuid4())
    body = {"payment_method": "card"}

    cache_key, replay = idempotency.begin("orders", key, body)
    assert replay is None

    with pytest.raises(IdempotencyConflict):
        idempotency.begin("orders", key, body)

    idempotency.complete(cache_key, {"reference": "KYS-AAA111"})
    _, replayed = idempotency.begin("orders", key, body)
    assert replayed == {"reference": "KYS-AAA111"}


def test_a_different_body_under_the_same_key_is_refused() -> None:
    """Standard Idempotency-Key semantics: a reused key carrying a changed body
    is a 4xx, not a second order at a different price.

    The body fingerprint used to be folded into the cache *key*, so a reused key
    with a different payload simply missed and placed another order.
    """
    key = str(uuid.uuid4())
    first, _ = idempotency.begin("orders", key, {"payment_method": "card"})
    idempotency.complete(first, {"reference": "KYS-AAA111"})

    with pytest.raises(IdempotencyKeyReuse):
        idempotency.begin("orders", key, {"payment_method": "cash"})


def test_an_abandoned_key_can_be_retried() -> None:
    """A failed attempt must not lock the customer out of trying again."""
    key = str(uuid.uuid4())
    body = {"payment_method": "card"}
    cache_key, _ = idempotency.begin("orders", key, body)
    idempotency.abandon(cache_key)

    _, replay = idempotency.begin("orders", key, body)
    assert replay is None


from conftest import requires_postgres  # noqa: E402


@requires_postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_kitchen_accepts_produce_one_transition(branch, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    """Two staff tapping Accept on the same ticket at the same moment."""
    order = Order.objects.create(
        branch=branch,
        payment_method="card",
        grand_total=1_000_000,
        guest_email="ada@example.com",
        status=OrderStatus.PAID,
    )

    def accept() -> str:
        try:
            transition(order, OrderStatus.CONFIRMED, actor=kitchen_user)
            return "ok"
        except IllegalTransition:
            return "rejected"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: accept(), range(4)))

    assert results.count("ok") == 1, results
    assert (
        OrderStatusEvent.objects.filter(order=order, to_status=OrderStatus.CONFIRMED).count() == 1
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED


@requires_postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_webhook_deliveries_settle_once(branch) -> None:  # type: ignore[no-untyped-def]
    """Providers retry aggressively; overlapping deliveries must credit once.

    The guard is the unique constraint on (provider, event_id), not a lock.
    """
    from django.db import IntegrityError

    from apps.payments.models import WebhookEvent

    def deliver() -> str:
        try:
            WebhookEvent.objects.create(
                provider="paystack",
                event_id="evt-concurrent",
                event_type="charge.success",
                signature_valid=True,
                payload={},
            )
            return "created"
        except IntegrityError:
            return "duplicate"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: deliver(), range(5)))

    assert results.count("created") == 1, results
    assert WebhookEvent.objects.filter(event_id="evt-concurrent").count() == 1


@requires_postgres
@pytest.mark.django_db(transaction=True)
def test_two_checkouts_cannot_both_redeem_a_one_use_code(branch, category, zone) -> None:  # type: ignore[no-untyped-def]
    """A ``usage_limit=1`` code, two customers confirming at the same moment.

    Both used to read ``times_used`` as 0 and both redeemed it. The row lock on
    the code serialises them: the loser blocks until the winner's redemption is
    committed, then either re-prices without the code or is refused outright.
    """
    from apps.accounts.models import Address, User
    from apps.carts.models import Cart
    from apps.carts.services import cart as svc
    from apps.catalog.models import MenuItem
    from apps.common.exceptions import PromoInvalid
    from apps.orders.services.placement import place_order
    from apps.promotions.models import DiscountType, PromoCode, PromoRedemption

    MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Burger",
        slug="burger",
        base_price=1_000_000,
        needs_repricing=False,
    )
    code = PromoCode.objects.create(
        branch=branch,
        code="ONLYONE",
        discount_type=DiscountType.FIXED,
        value=100_000,
        usage_limit=1,
    )

    baskets = []
    for index in range(2):
        shopper = User.objects.create_user(
            email=f"racer{index}@example.com", password="correct-horse-battery-staple"
        )
        basket = Cart.objects.create(branch=branch, user=shopper)
        svc.add_item(cart=basket, item_slug="burger", quantity=3)
        basket.delivery_address = Address.objects.create(
            user=shopper,
            label="home",
            recipient_name="Racer",
            phone="+2348012345678",
            street="1 Adeola Odeku Street",
            area="Victoria Island",
            city="Lagos",
            state="Lagos",
        )
        basket.promo_code = code
        basket.save()
        baskets.append(basket)

    def checkout(basket):  # type: ignore[no-untyped-def]
        try:
            place_order(cart=basket, payment_method="card")
            return "placed"
        except PromoInvalid:
            return "refused"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(checkout, baskets))

    assert PromoRedemption.objects.filter(promo_code=code).count() == 1, results
    assert Order.objects.filter(promo_code_snapshot=code.code).count() == 1, results
