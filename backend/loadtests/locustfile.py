"""Load profile for the Kuyash Place API.

Run against a Postgres staging environment — see README.md in this directory.

The mix is weighted to match real traffic: most requests are people browsing the
menu, a smaller number are customers watching an order they have placed, and
checkouts are comparatively rare but the most expensive thing the system does.

**Every scenario fails loudly when it cannot run.** The previous version of this
file had three scenarios that silently measured nothing: the order poller had no
order reference and returned immediately, the kitchen screen called a staff-only
endpoint with no credentials and measured a 403, and checkout paid by cash so the
payment provider was never touched. A load test that quietly measures nothing is
worse than no load test, because it reports success.
"""

from __future__ import annotations

import contextlib
import json
import os
import random
import threading
import time
import uuid
from collections import deque
from typing import Any

from locust import HttpUser, between, events, task

# ── Shared state ──────────────────────────────────────────────────────────────
# Orders placed during the run, so the pollers and socket watchers exercise real
# references instead of pretending. Locust users share a process per worker, so a
# lock is enough; each worker builds its own pool.

_PLACED: deque[tuple[str, str]] = deque(maxlen=500)  # (reference, guest_token)
_PLACED_LOCK = threading.Lock()


def remember_order(reference: str, guest_token: str) -> None:
    with _PLACED_LOCK:
        _PLACED.append((reference, guest_token))


def borrow_order() -> tuple[str, str] | None:
    with _PLACED_LOCK:
        return random.choice(_PLACED) if _PLACED else None  # noqa: S311 - test data, not crypto


def fail(name: str, message: str, started: float) -> None:
    """Record a scenario-level failure so it appears in the report."""
    events.request.fire(
        request_type="SCENARIO",
        name=name,
        response_time=(time.monotonic() - started) * 1000,
        response_length=0,
        exception=RuntimeError(message),
    )


def first_item_slug(client: Any) -> str | None:
    listing = client.get("/api/v1/catalog/items/?limit=1", name="menu list").json()
    results = listing.get("results") or []
    return results[0]["slug"] if results else None


# ── Browsing ──────────────────────────────────────────────────────────────────


class MenuBrowser(HttpUser):
    """The common case: someone reading the menu."""

    weight = 10
    wait_time = between(1, 4)

    def on_start(self) -> None:
        self.client.get("/api/v1/core/branch/", name="branch")

    @task(5)
    def browse_menu(self) -> None:
        self.client.get("/api/v1/catalog/items/", name="menu list")

    @task(2)
    def filter_menu(self) -> None:
        self.client.get(
            "/api/v1/catalog/items/?category=burgers&sort=popular", name="menu filtered"
        )

    @task(2)
    def search_menu(self) -> None:
        """Search is a primary navigation path and the most index-sensitive query."""
        term = random.choice(["burger", "jollof", "chicken", "rice", "grill"])  # noqa: S311
        self.client.get(f"/api/v1/catalog/items/?search={term}", name="menu search")

    @task(1)
    def view_item(self) -> None:
        # Deliberately a separate metric name: folding this into "menu list"
        # flattered that statistic in the previous version.
        listing = self.client.get(
            "/api/v1/catalog/items/?limit=1", name="menu list (for detail)"
        ).json()
        results = listing.get("results") or []
        if results:
            self.client.get(f"/api/v1/catalog/items/{results[0]['slug']}/", name="menu detail")


# ── Checkout ──────────────────────────────────────────────────────────────────


class CheckoutBase(HttpUser):
    """Shared cart construction. Subclasses choose how the order is paid."""

    abstract = True
    cart_token = ""

    def on_start(self) -> None:
        self.client.get("/api/v1/auth/csrf/", name="csrf")

    def csrf(self) -> str:
        return self.client.cookies.get("kuyash_csrftoken", "")

    def build_cart(self) -> dict[str, Any] | None:
        slug = first_item_slug(self.client)
        if slug is None:
            return None

        headers = {"X-Cart-Token": self.cart_token} if self.cart_token else {}
        added = self.client.post(
            "/api/v1/cart/items/",
            json={"menu_item": slug, "quantity": random.randint(1, 3)},  # noqa: S311
            headers={**headers, "X-CSRFToken": self.csrf()},
            name="cart add",
        )
        self.cart_token = added.headers.get("X-Cart-Token", self.cart_token)

        self.client.patch(
            "/api/v1/cart/fulfilment/",
            json={"fulfilment_type": "pickup"},
            headers={"X-Cart-Token": self.cart_token, "X-CSRFToken": self.csrf()},
            name="cart fulfilment",
        )
        cart: dict[str, Any] = self.client.get(
            "/api/v1/cart/", headers={"X-Cart-Token": self.cart_token}, name="cart read"
        ).json()
        return cart if cart.get("can_checkout") else None

    def place(self, cart: dict[str, Any], payment_method: str) -> dict[str, Any] | None:
        response = self.client.post(
            "/api/v1/orders/",
            json={
                "payment_method": payment_method,
                "expected_total": cart["totals"]["grand_total"]["amount"],
                "guest": {
                    "email": f"load-{uuid.uuid4().hex[:8]}@example.invalid",
                    "phone": "+2348000000000",
                    "full_name": "Load Test",
                },
            },
            headers={
                "X-Cart-Token": self.cart_token,
                "Idempotency-Key": str(uuid.uuid4()),
                "X-CSRFToken": self.csrf(),
            },
            name=f"order place ({payment_method})",
        )
        self.cart_token = ""
        if response.status_code != 201:
            return None
        order: dict[str, Any] = response.json()
        remember_order(order["reference"], order.get("guest_token", ""))
        return order


class CashCheckout(CheckoutBase):
    """Cash on delivery: no provider call, so this isolates our own cost."""

    weight = 1
    wait_time = between(5, 15)

    @task
    def checkout(self) -> None:
        cart = self.build_cart()
        if cart is not None:
            self.place(cart, "cash")


class CardCheckout(CheckoutBase):
    """Card: the expensive path, because it calls the payment provider.

    This is what the previous profile never exercised. Payment initialisation is
    an outbound HTTPS call inside the request, so it dominates checkout latency
    and is the first thing to saturate under load.
    """

    weight = 1
    wait_time = between(5, 15)

    @task
    def checkout(self) -> None:
        started = time.monotonic()
        cart = self.build_cart()
        if cart is None:
            return
        order = self.place(cart, "card")
        if order is None:
            return

        with self.client.post(
            "/api/v1/payments/initialise/",
            json={"order": order["reference"]},
            headers={"X-Guest-Token": order.get("guest_token", ""), "X-CSRFToken": self.csrf()},
            name="payment initialise",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"initialise returned {response.status_code}")
                return
            if not response.json().get("authorization_url"):
                response.failure("no authorization_url — the provider call did not happen")
                return
            response.success()
        del started


# ── Watching an order ─────────────────────────────────────────────────────────


class OrderPoller(HttpUser):
    """A customer watching an order, the polling fallback for the live socket.

    Polls with `If-None-Match`: a 304 with no body should cost almost nothing.
    """

    weight = 5
    wait_time = between(10, 20)

    def on_start(self) -> None:
        self.etag = ""
        self.order: tuple[str, str] | None = None
        self.waited_since = time.monotonic()

    @task
    def poll(self) -> None:
        if self.order is None:
            self.order = borrow_order()
        if self.order is None:
            # No order has been placed yet. Tolerate the ramp-up, then complain —
            # silence here is how this scenario measured nothing for months.
            if time.monotonic() - self.waited_since > 120:
                fail(
                    "order poll",
                    "no orders available to poll after 120s — is a checkout scenario running?",
                    self.waited_since,
                )
                self.waited_since = time.monotonic()
            return

        reference, guest_token = self.order
        headers = {"X-Guest-Token": guest_token}
        if self.etag:
            headers["If-None-Match"] = self.etag

        with self.client.get(
            f"/api/v1/orders/{reference}/",
            headers=headers,
            name="order poll",
            catch_response=True,
        ) as response:
            if response.status_code == 304:
                response.success()
            elif response.status_code == 200:
                self.etag = response.headers.get("ETag", "")
                response.success()
            elif response.status_code == 404:
                self.order = None  # it aged out of another worker's pool
                response.success()
            else:
                response.failure(f"unexpected {response.status_code}")


class OrderSocketWatcher(HttpUser):
    """The live path: a customer watching an order over a WebSocket.

    5,000 concurrent sockets is the scenario the product actually implies, and it
    was entirely unmeasured. Needs `websocket-client`; the scenario reports a
    failure rather than passing quietly when it is missing.
    """

    weight = 3
    wait_time = between(20, 40)

    @task
    def watch(self) -> None:
        started = time.monotonic()
        try:
            import websocket
        except ImportError:
            fail(
                "ws order",
                "websocket-client is not installed (pip install websocket-client)",
                started,
            )
            # Without the dependency the whole scenario is a lie; stop the run
            # rather than let it report a pass.
            if self.environment.runner is not None:
                self.environment.runner.quit()
            return

        borrowed = borrow_order()
        if borrowed is None:
            return
        reference, guest_token = borrowed

        url = self.host.replace("https://", "wss://").replace("http://", "ws://")
        socket = None
        try:
            socket = websocket.create_connection(
                f"{url}/ws/orders/{reference}/",
                timeout=20,
                origin=self.host,
                header=[f"Origin: {self.host}"],
            )
            if guest_token:
                socket.send(json.dumps({"type": "auth", "token": guest_token}))
            socket.recv()  # the first push: the order as it stands
            events.request.fire(
                request_type="WS",
                name="ws order first message",
                response_time=(time.monotonic() - started) * 1000,
                response_length=0,
                exception=None,
            )
            # Hold the socket open the way a real customer's tab would.
            socket.settimeout(15)
            # A quiet socket is the expected case: most orders do not change
            # while a customer is watching. Nothing to record either way.
            with contextlib.suppress(Exception):
                socket.recv()
        except Exception as exc:
            fail("ws order", f"{exc.__class__.__name__}: {exc}", started)
        finally:
            if socket is not None:
                socket.close()


# ── Staff ─────────────────────────────────────────────────────────────────────


class KitchenDisplay(HttpUser):
    """A KDS screen polling the queue.

    Authenticates for real. The previous version called a staff-only endpoint
    with no session and measured a permission check at ~5ms, which is why the
    "no lock contention" target looked comfortably met.
    """

    weight = 1
    wait_time = between(9, 11)

    def on_start(self) -> None:
        self.ready = False
        email = os.environ.get("KDS_EMAIL", "")
        password = os.environ.get("KDS_PASSWORD", "")
        started = time.monotonic()
        if not email or not password:
            fail(
                "kds queue",
                "KDS_EMAIL/KDS_PASSWORD not set — the kitchen scenario cannot run",
                started,
            )
            return

        self.client.get("/api/v1/auth/csrf/", name="csrf")
        login = self.client.post(
            "/api/v1/auth/login/",
            json={"email": email, "password": password},
            headers={"X-CSRFToken": self.client.cookies.get("kuyash_csrftoken", "")},
            name="kds login",
        )
        if login.status_code != 200:
            fail("kds queue", f"kitchen login failed ({login.status_code})", started)
            return
        self.ready = True

    @task(3)
    def poll_queue(self) -> None:
        if not self.ready:
            return
        with self.client.get(
            "/api/v1/kds/orders/", name="kds queue", catch_response=True
        ) as response:
            if response.status_code == 403:
                response.failure("403 — the account is not in the kitchen group")
            elif response.status_code == 200:
                response.success()

    @task(1)
    def poll_summary(self) -> None:
        if not self.ready:
            return
        self.client.get("/api/v1/kds/summary/", name="kds summary")
