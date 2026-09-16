"""Rate limits for the payment endpoints.

Two endpoints here are unauthenticated by design — the provider's webhook, where
the signature is the authentication, and the customer's return from hosted
checkout, which has no session for a guest — and both spend an outbound provider
call per request. Neither had any limit at all.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.throttling import WriteScopedRateThrottle


class ProviderCallRateThrottle(WriteScopedRateThrottle):
    """A scoped limit that counts reads too.

    :class:`WriteScopedRateThrottle` deliberately lets ``GET`` through: reading
    your own order history must not use up the allowance for placing an order.
    That reasoning does not survive here, where a ``GET`` is a request to
    Paystack on our account.

    Subclassed rather than written from scratch so a view can install both: the
    structural test in ``apps/common/tests/test_scoped_throttles.py`` asserts
    that every scoped view carries the write throttle itself, and on a read-only
    view that one is a no-op, so nothing is counted twice.
    """

    def allow_request(self, request: Request, view: APIView) -> bool:
        return ScopedRateThrottle.allow_request(self, request, view)
