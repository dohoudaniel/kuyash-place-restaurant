"""Idempotency-Key support.

Makes a double-tapped "Confirm Order" button safe: the second request replays
the first response instead of placing a second order and taking a second
payment.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.cache import cache

from apps.common.exceptions import IdempotencyConflict

HEADER = "Idempotency-Key"
TTL_SECONDS = 60 * 60 * 24  # 24 hours
#: Marker for a claimed-but-unfinished request.
#:
#: Compared by **value**, never by identity: a cache round-trip pickles and
#: unpickles the value, so the object that comes back is never the object that
#: went in. An identity check here silently never matched, which meant two
#: genuinely concurrent submissions could both proceed — the exact failure
#: Idempotency-Key exists to prevent.
_IN_FLIGHT = "__kuyash_idempotency_in_flight__"


def _key(scope: str, value: str, body: Any) -> str:
    fingerprint = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f"idem:{scope}:{value}:{fingerprint}"


def begin(scope: str, value: str, body: Any) -> tuple[str, Any | None]:
    """Claim an idempotency key.

    Returns the cache key and any stored response. A key that is claimed but
    has no stored response yet means an identical request is still running.
    """
    cache_key = _key(scope, value, body)
    existing = cache.get(cache_key)
    if existing == _IN_FLIGHT:
        raise IdempotencyConflict(
            "An identical request is still being processed. Please wait a moment."
        )
    if existing is not None:
        return cache_key, existing
    cache.set(cache_key, _IN_FLIGHT, TTL_SECONDS)
    return cache_key, None


def complete(cache_key: str, response_body: Any) -> None:
    cache.set(cache_key, response_body, TTL_SECONDS)


def abandon(cache_key: str) -> None:
    """Release a claim so a failed request can be retried."""
    cache.delete(cache_key)
