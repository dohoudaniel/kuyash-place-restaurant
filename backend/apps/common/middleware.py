"""Request middleware."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.common.logging import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """Assigns (or honours) a request ID and echoes it back.

    Accepts an inbound ``X-Request-ID`` from a trusted proxy so a trace spans
    the load balancer, the API and the Celery task it queued.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming[:64] if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response
