"""Problem-details handler tests.

Every error the API emits passes through here, so its shape is a contract the
frontend switches on. See docs/API_SPEC.md §0.2.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions

from apps.common.exceptions import (
    BelowMinimumOrder,
    BranchClosed,
    DomainError,
    IdempotencyConflict,
    IllegalTransition,
    ItemUnavailable,
    OutsideDeliveryArea,
    PaymentFailed,
    PriceChanged,
    PromoInvalid,
    problem_detail_handler,
)


def handle(exc: Exception):  # type: ignore[no-untyped-def]
    return problem_detail_handler(exc, {})


def test_domain_error_becomes_a_problem_document() -> None:
    response = handle(PriceChanged("Prices moved while you were checking out."))
    assert response is not None
    assert response.status_code == 409
    assert response.data == {
        "type": "https://api.kuyashplace.com/errors/price-changed",
        "title": "Prices changed while you were checking out",
        "status": 409,
        "code": "price_changed",
        "detail": "Prices moved while you were checking out.",
    }


def test_domain_error_carries_structured_extras() -> None:
    """`items` lets the UI highlight exactly which lines are the problem."""
    response = handle(ItemUnavailable("Chef's Special Pasta sold out.", items=["chefs-pasta"]))
    assert response is not None
    assert response.data["items"] == ["chefs-pasta"]


def test_domain_error_falls_back_to_its_title() -> None:
    response = handle(BranchClosed())
    assert response is not None
    assert response.data["detail"] == "We are not accepting orders right now"


@pytest.mark.parametrize(
    ("error", "code", "status_code"),
    [
        (PriceChanged, "price_changed", 409),
        (ItemUnavailable, "item_unavailable", 409),
        (BranchClosed, "branch_closed", 409),
        (PromoInvalid, "promo_invalid", 422),
        (OutsideDeliveryArea, "outside_delivery_area", 422),
        (BelowMinimumOrder, "below_minimum_order", 422),
        (IllegalTransition, "illegal_transition", 409),
        (IdempotencyConflict, "idempotency_conflict", 409),
        (PaymentFailed, "payment_failed", 402),
        (DomainError, "domain_error", 400),
    ],
)
def test_every_domain_error_has_a_stable_code(
    error: type[DomainError], code: str, status_code: int
) -> None:
    response = handle(error())
    assert response is not None
    assert response.data["code"] == code
    assert response.status_code == status_code


def test_validation_errors_are_reported_per_field() -> None:
    response = handle(drf_exceptions.ValidationError({"phone": ["Enter a valid number."]}))
    assert response is not None
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["errors"]["phone"] == ["Enter a valid number."]


def test_django_validation_errors_are_translated() -> None:
    response = handle(DjangoValidationError({"email": ["Already taken."]}))
    assert response is not None
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"


def test_http404_becomes_not_found() -> None:
    response = handle(Http404())
    assert response is not None
    assert response.status_code == 404
    assert response.data["code"] == "not_found"


def test_django_permission_denied_is_translated() -> None:
    response = handle(DjangoPermissionDenied())
    assert response is not None
    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"


def test_unauthenticated_maps_to_authentication_required() -> None:
    response = handle(drf_exceptions.NotAuthenticated())
    assert response is not None
    assert response.status_code == 401
    assert response.data["code"] == "authentication_required"


def test_throttling_reports_retry_after() -> None:
    response = handle(drf_exceptions.Throttled(wait=42))
    assert response is not None
    assert response.status_code == 429
    assert response.data["code"] == "rate_limited"
    assert response.data["retry_after"] == 42
    assert response["Retry-After"] == "42"


def test_throttling_without_a_wait_omits_the_header() -> None:
    response = handle(drf_exceptions.Throttled())
    assert response is not None
    assert response.data["code"] == "rate_limited"


def test_method_not_allowed_is_mapped() -> None:
    response = handle(drf_exceptions.MethodNotAllowed("POST"))
    assert response is not None
    assert response.data["code"] == "method_not_allowed"


def test_unhandled_exceptions_are_not_leaked() -> None:
    """An unexpected error returns None so DRF produces an opaque 500.

    A traceback must never reach a customer.
    """
    assert handle(ValueError("some internal detail")) is None
