"""Operational endpoints."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def health_check(request: HttpRequest) -> JsonResponse:
    """Liveness/readiness probe for the platform health check.

    Reports component status individually so a failing cache does not look like
    a failing database.
    """
    checks: dict[str, Any] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        cache.set("health-check", "ok", 5)
        checks["cache"] = "ok" if cache.get("health-check") == "ok" else "error: read-back failed"
    except Exception as exc:
        checks["cache"] = f"error: {exc.__class__.__name__}"

    checks["celery"] = "eager" if settings.CELERY_TASK_ALWAYS_EAGER else "broker"
    if not settings.CELERY_TASK_ALWAYS_EAGER:
        from apps.common.tasks import scheduler_status

        # Reported, never an "error": a stopped beat must be fixed, but restarting
        # the web process (what a failing probe triggers) would not fix it.
        checks["scheduler"] = scheduler_status()

    healthy = all(not str(value).startswith("error") for value in checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )


def _problem_response(request: HttpRequest, *, code: str, title: str, status: int) -> JsonResponse:
    return JsonResponse(
        {
            "type": f"https://api.kuyashplace.com/errors/{code.replace('_', '-')}",
            "title": title,
            "status": status,
            "code": code,
        },
        status=status,
        content_type="application/problem+json",
    )


def api_not_found(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    """Project-wide 404 handler.

    Without this, a mistyped API path returns Django's HTML error page and the
    frontend's `response.json()` throws a parse error instead of surfacing a
    useful code. Every API response is JSON, including the failures.
    """
    return _problem_response(
        request, code="not_found", title="That endpoint does not exist", status=404
    )


def api_server_error(request: HttpRequest) -> JsonResponse:
    """Project-wide 500 handler. Opaque on purpose — never leak internals."""
    return _problem_response(
        request,
        code="internal_error",
        title="Something went wrong on our side",
        status=500,
    )


def api_permission_denied(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _problem_response(
        request, code="permission_denied", title="You do not have access", status=403
    )


def api_bad_request(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _problem_response(request, code="bad_request", title="Malformed request", status=400)
