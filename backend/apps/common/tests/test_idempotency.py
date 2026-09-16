"""Idempotency-Key claiming.

The property under test is the one the old suite could not see: it called
``begin()`` twice **sequentially in one thread**, which passes just as happily
against a check-then-set implementation as against an atomic one. The race that
loses money needs real threads.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.common import idempotency
from apps.common.exceptions import IdempotencyConflict, IdempotencyKeyReuse

BODY = {"payment_method": "card"}


def new_key() -> str:
    return str(uuid.uuid4())


# ── Claiming ──────────────────────────────────────────────────────────────────


def test_a_second_claim_while_the_first_is_in_flight_is_refused() -> None:
    """The second holder of a key in flight is refused, not queued.

    This is what stops a double-tapped Confirm button taking two payments.
    """
    key = new_key()
    claim, replay = idempotency.begin("orders", key, BODY)
    assert replay is None

    with pytest.raises(IdempotencyConflict):
        idempotency.begin("orders", key, BODY)

    idempotency.complete(claim, {"reference": "KYS-AAA111"})
    _, replayed = idempotency.begin("orders", key, BODY)
    assert replayed == {"reference": "KYS-AAA111"}


def test_an_abandoned_key_can_be_retried() -> None:
    """A failed attempt must not lock the customer out of trying again."""
    key = new_key()
    claim, _ = idempotency.begin("orders", key, BODY)
    idempotency.abandon(claim)

    _, replay = idempotency.begin("orders", key, BODY)
    assert replay is None


def test_scopes_do_not_collide() -> None:
    """The same UUID against two endpoints is two independent requests."""
    key = new_key()
    idempotency.begin("orders", key, BODY)
    _, replay = idempotency.begin("reservations", key, BODY)
    assert replay is None


# ── A changed body under a reused key ─────────────────────────────────────────


def test_a_different_body_under_a_completed_key_is_refused() -> None:
    """Previously this silently placed a second order at a different price.

    The fingerprint used to be folded into the cache key, so a reused key with a
    changed payload simply missed the cache and sailed through as a new request.
    """
    key = new_key()
    claim, _ = idempotency.begin("orders", key, {"payment_method": "card"})
    idempotency.complete(claim, {"reference": "KYS-AAA111"})

    with pytest.raises(IdempotencyKeyReuse):
        idempotency.begin("orders", key, {"payment_method": "cash"})


def test_a_different_body_while_the_first_is_in_flight_is_refused() -> None:
    key = new_key()
    idempotency.begin("orders", key, {"payment_method": "card"})

    with pytest.raises(IdempotencyKeyReuse):
        idempotency.begin("orders", key, {"payment_method": "cash"})


def test_key_reuse_is_a_422_the_frontend_can_branch_on() -> None:
    error = IdempotencyKeyReuse()
    assert error.code == "idempotency_key_reuse"
    assert error.status_code == 422


def test_the_fingerprint_ignores_key_order() -> None:
    """A re-serialised body is the same request, not a conflicting one."""
    key = new_key()
    claim, _ = idempotency.begin("orders", key, {"a": 1, "b": 2})
    idempotency.complete(claim, {"reference": "KYS-AAA111"})

    _, replayed = idempotency.begin("orders", key, {"b": 2, "a": 1})
    assert replayed == {"reference": "KYS-AAA111"}


# ── Expiry ────────────────────────────────────────────────────────────────────


def test_an_unfinished_claim_expires_long_before_a_stored_response(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A crash mid-request must not lock the key for 24 hours.

    The in-flight marker and the stored response are written with deliberately
    different lifetimes; that difference is the fix, so it is asserted directly.
    """
    timeouts: dict[str, object] = {}
    real_add, real_set = cache.add, cache.set

    def spy_add(key, value, timeout=None, **kwargs):  # type: ignore[no-untyped-def]
        timeouts["add"] = timeout
        return real_add(key, value, timeout, **kwargs)

    def spy_set(key, value, timeout=None, **kwargs):  # type: ignore[no-untyped-def]
        timeouts["set"] = timeout
        return real_set(key, value, timeout, **kwargs)

    monkeypatch.setattr(cache, "add", spy_add)
    monkeypatch.setattr(cache, "set", spy_set)

    claim, _ = idempotency.begin("orders", new_key(), BODY)
    idempotency.complete(claim, {"reference": "KYS-AAA111"})

    assert 30 <= idempotency.IN_FLIGHT_TTL_SECONDS <= 60
    assert timeouts["add"] == idempotency.IN_FLIGHT_TTL_SECONDS
    assert timeouts["set"] == idempotency.TTL_SECONDS
    assert timeouts["add"] != timeouts["set"]


def test_a_claim_freed_by_expiry_can_be_reclaimed() -> None:
    """Simulates the crashed request whose marker has since timed out."""
    key = new_key()
    claim, _ = idempotency.begin("orders", key, BODY)
    cache.delete(claim.cache_key)  # what the short TTL does on its own

    _, replay = idempotency.begin("orders", key, BODY)
    assert replay is None


# ── The race that loses money ─────────────────────────────────────────────────


def test_concurrent_claims_admit_exactly_one() -> None:
    """**The regression test for the P0.** Eight threads, one key, one winner.

    Every thread blocks on a barrier so they all reach the claim at the same
    instant. Against the old check-then-set this admits several; against
    ``cache.add`` exactly one wins, because LocMemCache serialises ``add``
    under a lock and Redis does it as a single ``SETNX``.
    """
    key = new_key()
    workers = 8
    barrier = threading.Barrier(workers)

    def attempt(_index: int) -> str:
        barrier.wait()
        try:
            idempotency.begin("orders", key, BODY)
        except IdempotencyConflict:
            return "refused"
        return "claimed"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(attempt, range(workers)))

    assert outcomes.count("claimed") == 1, outcomes
    assert outcomes.count("refused") == workers - 1, outcomes


def test_concurrent_claims_with_conflicting_bodies_admit_one_and_refuse_the_rest() -> None:
    """Concurrency and a changed payload at once: still exactly one winner."""
    key = new_key()
    workers = 6
    barrier = threading.Barrier(workers)

    def attempt(index: int) -> str:
        barrier.wait()
        try:
            idempotency.begin("orders", key, {"payment_method": "card", "n": index})
        except (IdempotencyConflict, IdempotencyKeyReuse):
            return "refused"
        return "claimed"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(attempt, range(workers)))

    assert outcomes.count("claimed") == 1, outcomes


# ── The decorator ─────────────────────────────────────────────────────────────

_CALLS: list[str] = []
_FAIL_ONCE: list[bool] = []


class _Booking(APIView):
    """Stand-in for the three create views that share this mechanism."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @idempotency.idempotent("test_scope", message="Send an Idempotency-Key header.")
    def post(self, request):  # type: ignore[no-untyped-def]
        _CALLS.append("ran")
        if _FAIL_ONCE:
            _FAIL_ONCE.pop()
            raise ValueError("the service refused")
        return Response({"reference": f"RSV-{len(_CALLS)}"}, status=201)


@pytest.fixture(autouse=True)
def _reset_view_state():  # type: ignore[no-untyped-def]
    _CALLS.clear()
    _FAIL_ONCE.clear()
    yield
    _CALLS.clear()
    _FAIL_ONCE.clear()


def post(key: str | None = None):  # type: ignore[no-untyped-def]
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    request = APIRequestFactory().post("/x/", {"party_size": 2}, format="json", **headers)
    return _Booking.as_view()(request)


def test_the_decorator_requires_the_header() -> None:
    response = post()
    assert response.status_code == 400
    assert response.data["code"] == "idempotency_key_required"
    assert _CALLS == []


def test_the_decorator_replays_rather_than_running_twice() -> None:
    key = new_key()
    first = post(key)
    second = post(key)

    assert first.status_code == second.status_code == 201
    assert first.data == second.data
    assert second[idempotency.REPLAY_HEADER] == "true"
    assert _CALLS == ["ran"], "the view body ran twice"


def test_the_decorator_releases_the_key_when_the_view_fails() -> None:
    """A refused booking must not burn the key the customer retries with."""
    key = new_key()
    _FAIL_ONCE.append(True)

    with pytest.raises(ValueError):
        post(key)

    retried = post(key)
    assert retried.status_code == 201
    assert _CALLS == ["ran", "ran"]


def test_a_replay_is_not_marked_on_the_first_response() -> None:
    assert idempotency.REPLAY_HEADER not in post(new_key())
