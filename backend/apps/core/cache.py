"""Read-through caching for the handful of rows every request reads.

The audit's finding was blunt: *nothing* was cached anywhere, while
``get_current_branch()`` was called from 38 places and ``/core/branch/`` cost
around twenty queries on a page the frontend loads on every navigation.

Three rules shape what is here:

1. **Only rows that change rarely and are read constantly.** The branch, its
   schedule, site settings, legal copy, the FAQ, loyalty tiers and the category
   list. Carts, orders and anything money-bearing are never cached.
2. **Invalidation is a signal, not a TTL.** Every cached entry is dropped by a
   ``post_save``/``post_delete`` receiver on the model behind it. The TTL is the
   backstop for a receiver that was never wired up, not the mechanism.
3. **A per-request memo on top.** Within one request the branch is read once
   even though a dozen call sites ask for it. The memo exists only between
   ``request_started`` and ``request_finished``: outside a request — in a Celery
   task, a management command or a test calling a selector directly — there is
   no memo, so nothing can go stale in a long-lived worker thread.

``cache.get`` can return ``None`` both for "not cached" and for "cached ``None``".
Nothing here caches a ``None`` value, so the ambiguity never arises: a missing
branch raises rather than caching the absence.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from typing import Any

from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.utils.cache import patch_cache_control
from rest_framework.request import Request
from rest_framework.response import Response

# ── Time to live ──────────────────────────────────────────────────────────────
# Short enough that a missed invalidation heals by itself within a service,
# long enough that the hot path is a hit.
TTL_SHORT = 30
TTL_MEDIUM = 300
TTL_LONG = 3600

# ── Keys ──────────────────────────────────────────────────────────────────────
#: Declared in ``selectors`` since the first commit and never used until now.
CURRENT_BRANCH_CACHE_KEY = "core:current_branch"
OPENING_HOURS_KEY = "core:opening-hours:{branch}"
HOLIDAYS_KEY = "core:holidays:{branch}"
SITE_SETTINGS_KEY = "core:site-settings"
LEGAL_INDEX_KEY = "core:legal:index"
LEGAL_PAGE_KEY = "core:legal:page:{slug}"
FAQ_KEY = "support:faq:{category}"
FAQ_PREFIX = "support:faq:"
LOYALTY_PROGRAMME_KEY = "loyalty:programme"
CATEGORIES_KEY = "catalog:categories:{branch}"
CATEGORIES_PREFIX = "catalog:categories:"
SALES_REPORT_KEY = "reporting:sales:{branch}:{start}:{end}"

#: Keys whose exact name is not known at invalidation time (they carry a branch
#: id or a filter). Tracked here so a receiver can drop every variant.
_PREFIXED: dict[str, set[str]] = {}
_prefix_lock = threading.Lock()


# ── Per-request memo ──────────────────────────────────────────────────────────

_state = threading.local()


def _memo() -> dict[str, Any] | None:
    """The current request's memo, or ``None`` when no request is in flight."""
    return getattr(_state, "memo", None)


def _open_memo(**_kwargs: Any) -> None:
    _state.memo = {}


def _close_memo(**_kwargs: Any) -> None:
    _state.memo = None


def connect_memo() -> None:
    """Bind the memo's lifetime to the request. Called from ``CoreConfig.ready``."""
    request_started.connect(_open_memo, dispatch_uid="core.cache.open_memo", weak=False)
    request_finished.connect(_close_memo, dispatch_uid="core.cache.close_memo", weak=False)


# ── Read-through ──────────────────────────────────────────────────────────────


def cached[T](key: str, ttl: int, build: Callable[[], T]) -> T:
    """Return ``build()``'s result, from the memo, then the cache, then the database.

    ``build`` must return something picklable and must not return ``None`` —
    see the module docstring for why.
    """
    memo = _memo()
    if memo is not None and key in memo:
        return memo[key]

    value = cache.get(key)
    if value is None:
        value = build()
        cache.set(key, value, ttl)
        _remember_prefixed(key)
    if memo is not None:
        memo[key] = value
    return value


def _remember_prefixed(key: str) -> None:
    for prefix in (FAQ_PREFIX, CATEGORIES_PREFIX):
        if key.startswith(prefix):
            with _prefix_lock:
                _PREFIXED.setdefault(prefix, set()).add(key)


def invalidate(*keys: str) -> None:
    """Drop cached entries and the current request's memo of them."""
    for key in keys:
        cache.delete(key)
    memo = _memo()
    if memo is not None:
        for key in keys:
            memo.pop(key, None)


def invalidate_prefix(prefix: str) -> None:
    """Drop every variant of a key whose suffix varies (branch id, filter, …).

    Redis has no portable key scan through Django's cache API, so the variants
    actually written are tracked as they are written. A process that never wrote
    a variant has nothing of its own to drop, and its TTL bounds the staleness.
    """
    with _prefix_lock:
        keys = tuple(_PREFIXED.pop(prefix, ()))
    if keys:
        invalidate(*keys)


def invalidate_all(keys: Iterable[str] = (), prefixes: Iterable[str] = ()) -> None:
    invalidate(*keys)
    for prefix in prefixes:
        invalidate_prefix(prefix)


# ── HTTP caching ──────────────────────────────────────────────────────────────


class PublicCacheMixin:
    """``Cache-Control`` for endpoints that are genuinely public and identical for everyone.

    Only successful reads are marked. ``Vary: Cookie`` is added by Django's own
    session middleware the moment the session is touched, so a shared cache
    cannot hand one visitor's response to another even though this says
    ``public``.
    """

    #: Seconds a shared cache may serve this response without revalidating.
    cache_max_age = TTL_MEDIUM

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        finalized: Response = super().finalize_response(  # type: ignore[misc]
            request, response, *args, **kwargs
        )
        if request.method in {"GET", "HEAD"} and finalized.status_code == 200:
            patch_cache_control(finalized, public=True, max_age=self.cache_max_age)
        return finalized
