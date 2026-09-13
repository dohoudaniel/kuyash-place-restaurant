"""Scoped rate limits for write endpoints.

``throttle_scope`` on a view does nothing unless ``ScopedRateThrottle`` is among
the view's throttle classes, and it was not: the contact form, catering
enquiries, order placement and promo codes were limited only by the global
per-IP rate. Views with a scope now opt in explicitly through
:data:`SCOPED_THROTTLES`.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class WriteScopedRateThrottle(ScopedRateThrottle):
    """A scoped limit that counts writes only.

    Several scoped views also serve reads on the same path — ``/orders/`` lists
    order history — and reading your own orders must not use up the allowance
    for placing one.
    """

    def allow_request(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return super().allow_request(request, view)


#: The global limits plus the view's own scope.
SCOPED_THROTTLES = [AnonRateThrottle, UserRateThrottle, WriteScopedRateThrottle]
