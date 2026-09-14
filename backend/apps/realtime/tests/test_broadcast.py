"""Pushes are best-effort: a channel layer failure never fails an order."""

from __future__ import annotations

from typing import Any

import pytest

from apps.orders.models import Order
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition
from apps.realtime import broadcast

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    return place_order(cart=ready_cart, payment_method="card")


def test_a_broadcast_failure_never_breaks_an_order(order, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class Broken:
        async def group_send(self, *args: Any, **kwargs: Any) -> None:
            raise ConnectionError("redis is down")

    calls: list[str] = []
    real = broadcast.broadcast_order

    def spy(reference: str) -> None:
        calls.append(reference)
        real(reference)

    logged: list[str] = []
    monkeypatch.setattr(broadcast, "get_channel_layer", lambda: Broken())
    monkeypatch.setattr(broadcast, "broadcast_order", spy)
    # The project's logging config does not propagate app loggers to the root
    # handler caplog listens on, so record the call itself.
    monkeypatch.setattr(
        broadcast.logger, "exception", lambda message, **kwargs: logged.append(message)
    )
    transition(order, "paid")  # does not raise
    order.refresh_from_db()
    assert order.status == "paid"
    assert calls == [order.reference]
    assert logged == ["realtime_broadcast_failed"]


def test_broadcasting_a_missing_order_is_a_no_op() -> None:
    broadcast.broadcast_order("KYS-GONE00")


def test_one_push_per_order_per_transaction(order, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from django.db import transaction as db

    pushed: list[str] = []
    monkeypatch.setattr(broadcast, "broadcast_order", pushed.append)
    with db.atomic():
        broadcast.broadcast_after_commit(order)
        broadcast.broadcast_after_commit(order)
    assert pushed == [order.reference]


def test_a_rolled_back_change_does_not_block_the_next_push(order, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from django.db import transaction as db

    pushed: list[str] = []
    monkeypatch.setattr(broadcast, "broadcast_order", pushed.append)
    with pytest.raises(RuntimeError), db.atomic():
        broadcast.broadcast_after_commit(order)
        raise RuntimeError("rolled back")
    assert pushed == []
    with db.atomic():
        broadcast.broadcast_after_commit(order)
    assert pushed == [order.reference]
