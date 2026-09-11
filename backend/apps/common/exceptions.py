"""Domain errors and the RFC 7807 problem-details exception handler."""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

ERROR_BASE_URL = "https://api.kuyashplace.com/errors/"


class DomainError(Exception):
    """Base class for business-rule violations.

    Subclasses carry a machine-readable ``code`` the frontend switches on, and a
    human-readable message safe to show a customer.
    """

    # Annotated so subclasses may override with a different code/status; without
    # these, mypy infers Literal types from the base and rejects every subclass.
    code: str = "domain_error"
    status_code: int = status.HTTP_400_BAD_REQUEST
    title: str = "Request could not be completed"

    def __init__(self, detail: str = "", **extra: Any) -> None:
        self.detail = detail or self.title
        self.extra = extra
        super().__init__(self.detail)


class PriceChanged(DomainError):
    code = "price_changed"
    status_code = status.HTTP_409_CONFLICT
    title = "Prices changed while you were checking out"


class ItemUnavailable(DomainError):
    code = "item_unavailable"
    status_code = status.HTTP_409_CONFLICT
    title = "An item in your cart is no longer available"


class BranchClosed(DomainError):
    code = "branch_closed"
    status_code = status.HTTP_409_CONFLICT
    title = "We are not accepting orders right now"


class PromoInvalid(DomainError):
    code = "promo_invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    title = "That promo code cannot be applied"


class OutsideDeliveryArea(DomainError):
    code = "outside_delivery_area"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    title = "We do not deliver to that address yet"


class BelowMinimumOrder(DomainError):
    code = "below_minimum_order"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    title = "Order is below the minimum for this area"


class IllegalTransition(DomainError):
    code = "illegal_transition"
    status_code = status.HTTP_409_CONFLICT
    title = "That status change is not allowed"


class IdempotencyConflict(DomainError):
    code = "idempotency_conflict"
    status_code = status.HTTP_409_CONFLICT
    title = "An identical request is still being processed"


class PaymentFailed(DomainError):
    code = "payment_failed"
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    title = "Payment could not be completed"


# Maps DRF exception classes to our stable error codes.
_DRF_CODES: dict[type[Exception], str] = {
    drf_exceptions.NotAuthenticated: "authentication_required",
    drf_exceptions.AuthenticationFailed: "authentication_required",
    drf_exceptions.PermissionDenied: "permission_denied",
    drf_exceptions.NotFound: "not_found",
    drf_exceptions.ValidationError: "validation_error",
    drf_exceptions.Throttled: "rate_limited",
    drf_exceptions.MethodNotAllowed: "method_not_allowed",
    drf_exceptions.ParseError: "malformed_request",
    drf_exceptions.UnsupportedMediaType: "unsupported_media_type",
}


def _problem(
    *,
    code: str,
    title: str,
    status_code: int,
    detail: str = "",
    **extra: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"{ERROR_BASE_URL}{code.replace('_', '-')}",
        "title": title,
        "status": status_code,
        "code": code,
    }
    if detail:
        body["detail"] = detail
    body.update(extra)
    return body


def problem_detail_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF exception handler producing RFC 7807 problem documents.

    Every error the API emits has the same shape and a stable ``code``, so the
    frontend can branch on the code instead of parsing prose.
    """
    if isinstance(exc, DomainError):
        return Response(
            _problem(
                code=exc.code,
                title=exc.title,
                status_code=exc.status_code,
                detail=exc.detail,
                **exc.extra,
            ),
            status=exc.status_code,
        )

    if isinstance(exc, DjangoValidationError):
        detail: Any = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        exc = drf_exceptions.ValidationError(detail=detail)
    elif isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf_exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled: log it and return an opaque 500. Never leak a traceback.
        logger.exception("unhandled_exception", exc_info=exc)
        return None

    code = next(
        (value for klass, value in _DRF_CODES.items() if isinstance(exc, klass)),
        "error",
    )
    title = getattr(exc, "default_detail", response.status_text)

    if isinstance(exc, drf_exceptions.ValidationError):
        body = _problem(
            code=code,
            title="One or more fields were invalid",
            status_code=response.status_code,
            errors=response.data,
        )
    else:
        message = response.data.get("detail") if isinstance(response.data, dict) else None
        body = _problem(
            code=code,
            title=str(title),
            status_code=response.status_code,
            detail=str(message) if message else "",
        )
        wait = getattr(exc, "wait", None)
        if isinstance(exc, drf_exceptions.Throttled) and wait:
            body["retry_after"] = int(wait)
            response["Retry-After"] = str(int(wait))

    response.data = body
    return response
