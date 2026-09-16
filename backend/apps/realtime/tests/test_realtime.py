"""Live order tracking and kitchen queue over WebSockets (Phase 3.6)."""

from __future__ import annotations

from typing import Any

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Group

from apps.accounts.models import User
from apps.orders.models import Order
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition
from apps.realtime import consumers
from apps.realtime.routing import websocket_urlpatterns

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]

ROUTER = URLRouter(websocket_urlpatterns)


def socket(path: str, user: Any = None) -> WebsocketCommunicator:
    communicator = WebsocketCommunicator(ROUTER, path)
    if user is not None:
        communicator.scope["user"] = user
    return communicator


@pytest.fixture
def order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    return place_order(cart=ready_cart, payment_method="card")


@pytest.fixture
def guest_order(order) -> Order:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(user=None, guest_email="guest@example.com")
    order.refresh_from_db()
    return order


@pytest.fixture
def kitchen_user(db) -> User:  # type: ignore[no-untyped-def]
    user = User.objects.create_user(email="kitchen@example.com", password="x" * 16)
    user.groups.add(Group.objects.get_or_create(name="kitchen")[0])
    return user


@pytest.fixture
def stranger(db) -> User:  # type: ignore[no-untyped-def]
    return User.objects.create_user(email="stranger@example.com", password="x" * 16)


# ──────────────────────────────────────────────────────────────────────────────
# Order tracking
# ──────────────────────────────────────────────────────────────────────────────


async def test_the_owner_gets_the_order_then_each_change(order, verified_user) -> None:  # type: ignore[no-untyped-def]
    ws = socket(f"/ws/orders/{order.reference}/", verified_user)
    connected, _ = await ws.connect()
    assert connected
    first = await ws.receive_json_from()
    assert first["type"] == "order"
    assert first["order"]["reference"] == order.reference
    assert first["order"]["status"] == "pending_payment"
    assert "guest_token" not in first["order"]

    await database_sync_to_async(transition)(order, "paid")
    update = await ws.receive_json_from(timeout=2)
    assert update["order"]["status"] == "paid"
    await ws.disconnect()


async def test_a_guest_authenticates_with_a_message(guest_order) -> None:  # type: ignore[no-untyped-def]
    ws = socket(f"/ws/orders/{guest_order.reference}/")
    assert (await ws.connect())[0]
    assert await ws.receive_nothing(timeout=0.2)  # nothing until the token is shown
    await ws.send_json_to({"type": "auth", "token": guest_order.guest_token})
    assert (await ws.receive_json_from())["order"]["reference"] == guest_order.reference
    await ws.send_json_to({"type": "auth", "token": "again"})  # already joined: ignored
    assert await ws.receive_nothing(timeout=0.2)
    await ws.disconnect()


@pytest.mark.parametrize("token", ["wrong", 12345, None])
async def test_a_wrong_token_closes_like_a_missing_order(guest_order, token) -> None:  # type: ignore[no-untyped-def]
    ws = socket(f"/ws/orders/{guest_order.reference}/")
    await ws.connect()
    await ws.send_json_to({"type": "auth", "token": token})
    closed = await ws.receive_output()
    assert closed == {"type": "websocket.close", "code": consumers.CLOSE_NOT_FOUND}


async def test_an_unknown_order_closes_the_same_way(db) -> None:  # type: ignore[no-untyped-def]
    ws = socket("/ws/orders/KYS-NOPE00/")
    await ws.connect()
    await ws.send_json_to({"type": "auth", "token": "anything"})
    assert (await ws.receive_output())["code"] == consumers.CLOSE_NOT_FOUND


async def test_other_customers_are_refused_at_the_handshake(order, stranger) -> None:  # type: ignore[no-untyped-def]
    """A signed-in visitor who is not the owner has nothing left to prove.

    The socket used to be accepted first and the check run afterwards, and a
    caller who failed it was simply left connected — no close, no idle timeout,
    no cap on how many they could hold open.
    """
    ws = socket(f"/ws/orders/{order.reference}/", stranger)
    connected, code = await ws.connect()
    assert not connected
    assert code == consumers.CLOSE_NOT_FOUND


@pytest.mark.parametrize("message", [{"type": "hello"}, ["not", "an", "object"], "plain"])
async def test_a_message_that_is_not_the_auth_message_closes_the_socket(
    guest_order, message
) -> None:  # type: ignore[no-untyped-def]
    """The only thing this socket ever expects to hear is the auth message."""
    ws = socket(f"/ws/orders/{guest_order.reference}/")
    await ws.connect()
    await ws.send_json_to(message)
    assert (await ws.receive_output())["code"] == consumers.CLOSE_FORBIDDEN


async def test_a_guest_who_never_proves_ownership_is_closed(guest_order, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Accepting is the only way to hear the token, so the window is bounded."""
    monkeypatch.setattr(consumers, "AUTH_TIMEOUT_SECONDS", 0.05)
    ws = socket(f"/ws/orders/{guest_order.reference}/")
    assert (await ws.connect())[0]
    closed = await ws.receive_output(timeout=2)
    assert closed == {"type": "websocket.close", "code": consumers.CLOSE_NOT_FOUND}


async def test_proving_ownership_cancels_the_deadline(guest_order, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(consumers, "AUTH_TIMEOUT_SECONDS", 0.05)
    ws = socket(f"/ws/orders/{guest_order.reference}/")
    await ws.connect()
    await ws.send_json_to({"type": "auth", "token": guest_order.guest_token})
    assert (await ws.receive_json_from())["order"]["reference"] == guest_order.reference
    assert await ws.receive_nothing(timeout=0.3)  # the deadline did not fire
    await ws.disconnect()


async def test_a_stranger_is_never_pushed_another_customers_order(order, stranger) -> None:  # type: ignore[no-untyped-def]
    ws = socket(f"/ws/orders/{order.reference}/", stranger)
    await ws.connect()
    await database_sync_to_async(transition)(order, "paid")
    assert await ws.receive_nothing(timeout=0.3)  # not in the group, so no push


async def test_staff_may_follow_any_order(order, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    ws = socket(f"/ws/orders/{order.reference}/", kitchen_user)
    await ws.connect()
    assert (await ws.receive_json_from())["type"] == "order"
    await ws.disconnect()


# ──────────────────────────────────────────────────────────────────────────────
# Kitchen queue
# ──────────────────────────────────────────────────────────────────────────────


async def test_the_kitchen_gets_the_queue_then_ticket_changes(order, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    await database_sync_to_async(transition)(order, "paid")
    ws = socket("/ws/kds/", kitchen_user)
    assert (await ws.connect())[0]
    queue = await ws.receive_json_from()
    assert queue["type"] == "queue"
    assert [ticket["reference"] for ticket in queue["orders"]] == [order.reference]
    assert "confirmed" in queue["statuses"]

    await database_sync_to_async(transition)(order, "confirmed", actor=kitchen_user)
    ticket = await ws.receive_json_from(timeout=2)
    assert ticket["type"] == "ticket"
    assert ticket["ticket"]["status"] == "confirmed"
    await ws.disconnect()


@pytest.mark.parametrize("who", ["anonymous", "customer"])
async def test_the_kitchen_socket_refuses_everyone_else(branch, verified_user, who) -> None:  # type: ignore[no-untyped-def]
    from django.contrib.auth.models import AnonymousUser

    ws = socket("/ws/kds/", AnonymousUser() if who == "anonymous" else verified_user)
    connected, code = await ws.connect()
    assert not connected
    assert code == consumers.CLOSE_FORBIDDEN


async def test_the_kitchen_socket_closes_on_anything_a_client_sends(order, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    """Server → client only. A client that talks here is not one of ours."""
    ws = socket("/ws/kds/", kitchen_user)
    await ws.connect()
    await ws.receive_json_from()  # the queue
    await ws.send_json_to({"type": "anything"})
    assert (await ws.receive_output())["code"] == consumers.CLOSE_FORBIDDEN


# ──────────────────────────────────────────────────────────────────────────────
# The full ASGI stack
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("origin", "allowed"), [(b"http://localhost:3000", True), (b"https://evil.example", False)]
)
async def test_the_handshake_origin_is_checked(order, origin, allowed) -> None:  # type: ignore[no-untyped-def]
    from config.asgi import application

    ws = WebsocketCommunicator(
        application,
        f"/ws/orders/{order.reference}/",
        headers=[(b"origin", origin), (b"host", b"localhost")],
    )
    connected, _ = await ws.connect()
    assert connected is allowed
    if connected:
        await ws.disconnect()
