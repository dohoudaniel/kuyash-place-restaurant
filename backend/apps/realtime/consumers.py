"""WebSocket consumers for order tracking and the kitchen queue (ADR-004, Phase 3.6).

They carry the same payloads as `GET /orders/{ref}/` and `GET /kds/orders/`, so
a client can fall back to polling those endpoints at any moment and see the
same data. Messages are server → client, apart from a guest's one `auth`
message.

**Authorisation comes before acceptance.** A socket used to be accepted first
and then checked, and a caller who failed the check was simply left connected —
no close, no timeout, no cap. A visitor who cannot possibly be authorised is now
refused at the handshake, and the one case that genuinely has to be accepted
first — a guest who proves ownership with a message, because there is no way to
hear a message before accepting — is given a few seconds and then closed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.realtime import access, payloads

#: Private close codes. 4403: not allowed. 4404: no such order, or not yours.
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404

#: How long a guest socket may stay open before it has proved which order it is
#: watching. Long enough for a page to finish loading and send its token, short
#: enough that unauthenticated sockets cannot be accumulated.
AUTH_TIMEOUT_SECONDS = 10


class OrderConsumer(AsyncJsonWebsocketConsumer):
    """`ws/orders/{reference}/` — live status for one order.

    A signed-in owner (or staff) is let in on connect. A guest connects, then
    sends `{"type": "auth", "token": "…"}` with the order's guest token — sent
    as a message rather than in the URL, so the token never lands in access
    logs. A wrong token and an unknown order close the socket the same way.
    """

    reference: str = ""
    joined: bool = False
    _deadline: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        self.reference = self.scope["url_route"]["kwargs"]["reference"]
        order = await database_sync_to_async(payloads.load_order)(self.reference)
        user = self.scope.get("user")

        if order is not None and await database_sync_to_async(access.may_watch_order)(user, order):
            await self.accept()
            await self._join(order)
            return

        if user is not None and getattr(user, "is_authenticated", False):
            # A signed-in visitor has already presented everything they have.
            # There is no token they could send that would change the answer, so
            # there is no reason to hold the socket open. An unknown order and
            # somebody else's order are refused identically.
            await self.close(code=CLOSE_NOT_FOUND)
            return

        # A guest may still hold the order's token. Accepting is the only way to
        # hear it, so accept — and start the clock.
        await self.accept()
        self._deadline = asyncio.create_task(self._close_if_unproven())

    async def _close_if_unproven(self) -> None:
        try:
            await asyncio.sleep(AUTH_TIMEOUT_SECONDS)
        except asyncio.CancelledError:  # pragma: no cover - joined or disconnected first
            return
        if not self.joined:
            await self.close(code=CLOSE_NOT_FOUND)

    def _cancel_deadline(self) -> None:
        if self._deadline is not None:
            self._deadline.cancel()
            self._deadline = None

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        if self.joined:
            # Already watching. Nothing a client sends afterwards means anything,
            # and a repeated `auth` is a retry, not an attack.
            return
        if not isinstance(content, dict) or content.get("type") != "auth":
            # The only message this socket accepts is the auth message. Anything
            # else is a client we do not recognise, so it does not get to sit
            # here sending more.
            await self.close(code=CLOSE_FORBIDDEN)
            return

        token = content.get("token")
        order = await database_sync_to_async(payloads.load_order)(self.reference)
        if (
            order is None
            or not isinstance(token, str)
            or not access.may_watch_order(None, order, token)
        ):
            await self.close(code=CLOSE_NOT_FOUND)
            return
        await self._join(order)

    async def _join(self, order: Any) -> None:
        self.joined = True
        self._cancel_deadline()
        await self.channel_layer.group_add(payloads.order_group(self.reference), self.channel_name)
        await self.send_json(
            {"type": "order", "order": await database_sync_to_async(payloads.order_payload)(order)}
        )

    async def disconnect(self, code: int) -> None:
        self._cancel_deadline()
        if self.joined:
            await self.channel_layer.group_discard(
                payloads.order_group(self.reference), self.channel_name
            )

    async def order_updated(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "order", "order": event["order"]})


class KitchenConsumer(AsyncJsonWebsocketConsumer):
    """`ws/kds/` — the ticket queue, then each ticket as it changes. Kitchen staff and managers."""

    group: str = ""

    async def connect(self) -> None:
        user = self.scope.get("user")
        # Group membership is a query: never run it on the event loop.
        if not await database_sync_to_async(access.may_watch_kitchen)(user):
            await self.close(code=CLOSE_FORBIDDEN)
            return
        branch = await database_sync_to_async(_current_branch)()
        self.group = payloads.kitchen_group(branch.pk)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        queue = await database_sync_to_async(payloads.queue_payload)(branch)
        await self.send_json(
            {"type": "queue", "orders": queue, "statuses": list(payloads.KDS_STATUSES)}
        )

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        """Server → client only. A client that talks here is not one of ours."""
        await self.close(code=CLOSE_FORBIDDEN)

    async def disconnect(self, code: int) -> None:
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def ticket_updated(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "ticket", "ticket": event["ticket"]})


def _current_branch() -> Any:
    from apps.core.selectors import get_current_branch

    return get_current_branch()
