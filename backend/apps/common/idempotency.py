"""Idempotency-Key support.

Makes a double-tapped "Confirm Order" button safe: the second request replays
the first response instead of placing a second order and taking a second
payment.

Three properties this has to hold, each of which it previously got wrong:

1. **The claim is atomic.** ``cache.add`` is a single ``SETNX`` on Redis, so of
   two genuinely concurrent requests exactly one wins. The previous
   ``get``-then-``set`` left a window in which both read "absent" and both
   proceeded — two orders, two payments.
2. **A changed body under a reused key is refused, not silently honoured.** The
   body fingerprint lives in the cached *value*. Folding it into the cache
   *key* meant a reused key carrying a different payload simply missed, and
   placed a second order at a different price. Standard Idempotency-Key
   semantics require a 4xx there.
3. **A crash does not lock the key until tomorrow.** The in-flight marker gets a
   short TTL; only a *completed* response is kept for 24 hours. A request whose
   process died mid-flight frees its key within a minute rather than refusing
   the customer for a day.

Views should use the :func:`idempotent` decorator rather than calling
:func:`begin`/:func:`complete`/:func:`abandon` by hand — the sequence was
copy-pasted into three views, and a missed ``abandon`` is a customer locked out
of retrying.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.exceptions import (
    IdempotencyConflict,
    IdempotencyKeyReuse,
    MissingIdempotencyKey,
)

HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotency-Replayed"

#: Attribute :func:`idempotent` sets on the request, holding the claimed key.
#: Read it with :func:`key_of` in views that persist the key on the row they
#: create — the durable backstop needs the same value the cache was keyed on.
REQUEST_ATTR = "idempotency_key"

#: How long a *completed* response stays replayable.
TTL_SECONDS = 60 * 60 * 24  # 24 hours

#: How long an *unfinished* claim is held before it frees itself.
#:
#: Deliberately short and separate from :data:`TTL_SECONDS`. A worker that dies
#: mid-request leaves its marker behind; at 24 hours that marker refused the
#: customer's every retry until the next day.
IN_FLIGHT_TTL_SECONDS = 45

#: Marker for a claimed-but-unfinished request.
#:
#: Compared by **value**, never by identity: a cache round-trip pickles and
#: unpickles the value, so the object that comes back is never the object that
#: went in. An identity check here silently never matched, which meant two
#: genuinely concurrent submissions could both proceed.
_IN_FLIGHT = "__kuyash_idempotency_in_flight__"

_STILL_RUNNING = "An identical request is still being processed. Please wait a moment."

_MISSING_KEY = "Send an Idempotency-Key header so a repeated submission cannot be processed twice."


@dataclass(frozen=True, slots=True)
class Claim:
    """A held idempotency key.

    Opaque to callers: hand it back to :func:`complete` or :func:`abandon`.
    """

    cache_key: str
    fingerprint: str


def fingerprint(body: Any) -> str:
    """A stable digest of a request body, insensitive to key order."""
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:32]


def _cache_key(scope: str, value: str) -> str:
    """Keyed on ``(scope, key)`` only — never on the body (see the module docstring)."""
    return f"idem:{scope}:{value}"


def _entry(body_fingerprint: str, response: Any) -> dict[str, Any]:
    return {"fingerprint": body_fingerprint, "response": response}


def begin(scope: str, value: str, body: Any) -> tuple[Claim, Any | None]:
    """Claim an idempotency key.

    Returns the claim and any stored response. A claim that is held but has no
    stored response yet means an identical request is still running.

    Raises :class:`IdempotencyKeyReuse` when the key was already used with a
    different body, and :class:`IdempotencyConflict` when the first request is
    still in flight.
    """
    cache_key = _cache_key(scope, value)
    body_fingerprint = fingerprint(body)
    claim = Claim(cache_key=cache_key, fingerprint=body_fingerprint)

    # Two attempts: `add` can lose to a claim that then expires before the read
    # below, which would otherwise report a conflict that no longer exists.
    for _attempt in range(2):
        if cache.add(cache_key, _entry(body_fingerprint, _IN_FLIGHT), IN_FLIGHT_TTL_SECONDS):
            return claim, None

        existing = cache.get(cache_key)
        if existing is None:
            continue

        if not isinstance(existing, dict) or existing.get("fingerprint") != body_fingerprint:
            raise IdempotencyKeyReuse(
                "This Idempotency-Key was already used for a different request. "
                "Send the original request unchanged, or use a new key."
            )

        stored = existing.get("response")
        if stored == _IN_FLIGHT:
            raise IdempotencyConflict(_STILL_RUNNING)
        return claim, stored

    raise IdempotencyConflict(_STILL_RUNNING)


def complete(claim: Claim, response_body: Any) -> None:
    """Store the response so a replay of this key returns it for 24 hours."""
    cache.set(claim.cache_key, _entry(claim.fingerprint, response_body), TTL_SECONDS)


def abandon(claim: Claim) -> None:
    """Release a claim so a failed request can be retried."""
    cache.delete(claim.cache_key)


def key_of(request: Request) -> str:
    """The Idempotency-Key :func:`idempotent` claimed for this request.

    For views that store the key on the row they create, so a unique constraint
    can catch a duplicate the cache let through.
    """
    return str(getattr(request, REQUEST_ATTR, "") or "")


ViewMethod = Callable[..., Response]


def idempotent(
    scope: str,
    *,
    message: str = "",
    replay_status: int = status.HTTP_201_CREATED,
) -> Callable[[ViewMethod], ViewMethod]:
    """Make a DRF view method idempotent on its ``Idempotency-Key`` header.

    Wraps the whole sequence that was previously copy-pasted into three views:
    require the header, claim the key, replay a stored response with
    ``Idempotency-Replayed: true``, and release the claim if the request fails
    so the customer can correct and retry.

    ``scope`` namespaces the key, so the same UUID used against orders and
    against reservations does not collide. ``message`` is what the customer is
    told when the header is missing; ``replay_status`` is the status a replayed
    response carries (201 for the create endpoints that use this).

    Apply it beneath ``@extend_schema`` so the generated OpenAPI is unaffected::

        @extend_schema(...)
        @idempotency.idempotent("reservations", message="…")
        def post(self, request: Request) -> Response:
            ...
    """

    def decorate(view_method: ViewMethod) -> ViewMethod:
        @functools.wraps(view_method)
        def wrapper(self: Any, request: Request, *args: Any, **kwargs: Any) -> Response:
            key = request.headers.get(HEADER, "").strip()
            if not key:
                raise MissingIdempotencyKey(message or _MISSING_KEY)
            setattr(request, REQUEST_ATTR, key)

            claim, replayed = begin(scope, key, request.data)
            if replayed is not None:
                response = Response(replayed, status=replay_status)
                response[REPLAY_HEADER] = "true"
                return response

            try:
                response = view_method(self, request, *args, **kwargs)
            except Exception:
                # Release the claim so the customer can correct and retry.
                abandon(claim)
                raise

            # Only a successful response with a body is worth replaying. A 4xx
            # is released so the corrected retry is a fresh request, and a body
            # of ``None`` would be indistinguishable from "never claimed".
            if response.status_code < 400 and response.data is not None:
                complete(claim, response.data)
            else:
                abandon(claim)
            return response

        return wrapper

    return decorate


__all__ = [
    "HEADER",
    "IN_FLIGHT_TTL_SECONDS",
    "REPLAY_HEADER",
    "REQUEST_ATTR",
    "TTL_SECONDS",
    "Claim",
    "abandon",
    "begin",
    "complete",
    "fingerprint",
    "idempotent",
    "key_of",
]
