"""Load profile for the Kuyash Place API.

Run against a Postgres staging environment — see README.md in this directory.

The mix is weighted to match real traffic: most requests are people browsing the
menu, a smaller number are customers polling an order they have already placed,
and placements are comparatively rare but the most expensive.
"""

from __future__ import annotations

import uuid

from locust import HttpUser, between, task


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

    @task(1)
    def view_item(self) -> None:
        listing = self.client.get("/api/v1/catalog/items/?limit=1", name="menu list").json()
        results = listing.get("results") or []
        if results:
            self.client.get(f"/api/v1/catalog/items/{results[0]['slug']}/", name="menu detail")


class OrderPoller(HttpUser):
    """A customer watching an order they have already placed.

    Polls with `If-None-Match`, which is the whole point of the ETag: a 304 with
    no body should cost almost nothing.
    """

    weight = 5
    wait_time = between(10, 20)
    reference = ""
    etag = ""

    @task
    def poll(self) -> None:
        if not self.reference:
            return
        headers = {"If-None-Match": self.etag} if self.etag else {}
        with self.client.get(
            f"/api/v1/orders/{self.reference}/",
            headers=headers,
            name="order poll",
            catch_response=True,
        ) as response:
            if response.status_code == 304:
                response.success()
            elif response.status_code == 200:
                self.etag = response.headers.get("ETag", "")
                response.success()


class Checkout(HttpUser):
    """The expensive path: build a cart and place an order."""

    weight = 1
    wait_time = between(5, 15)
    cart_token = ""

    def on_start(self) -> None:
        self.client.get("/api/v1/auth/csrf/", name="csrf")

    @task
    def place_order(self) -> None:
        listing = self.client.get("/api/v1/catalog/items/?limit=1", name="menu list").json()
        results = listing.get("results") or []
        if not results:
            return

        headers = {"X-Cart-Token": self.cart_token} if self.cart_token else {}
        added = self.client.post(
            "/api/v1/cart/items/",
            json={"menu_item": results[0]["slug"], "quantity": 1},
            headers=headers,
            name="cart add",
        )
        self.cart_token = added.headers.get("X-Cart-Token", self.cart_token)

        self.client.patch(
            "/api/v1/cart/fulfilment/",
            json={"fulfilment_type": "pickup"},
            headers={"X-Cart-Token": self.cart_token},
            name="cart fulfilment",
        )
        cart = self.client.get(
            "/api/v1/cart/", headers={"X-Cart-Token": self.cart_token}, name="cart read"
        ).json()
        if not cart.get("can_checkout"):
            return

        self.client.post(
            "/api/v1/orders/",
            json={
                "payment_method": "cash",
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
            },
            name="order place",
        )
        self.cart_token = ""


class KitchenDisplay(HttpUser):
    """A KDS screen polling the queue. Few clients, steady cadence."""

    weight = 1
    wait_time = between(9, 11)

    @task
    def poll_queue(self) -> None:
        self.client.get("/api/v1/kds/orders/", name="kds queue")
