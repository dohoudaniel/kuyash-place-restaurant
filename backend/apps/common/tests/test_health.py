"""Health endpoint tests."""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_reports_each_component(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get(reverse("health-check"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["cache"] == "ok"
    assert body["checks"]["celery"] in {"eager", "broker"}


def test_unknown_api_path_returns_json_not_html(client, settings) -> None:  # type: ignore[no-untyped-def]
    """A mistyped path must not return an HTML page.

    The frontend calls response.json() unconditionally; an HTML 404 surfaces as
    a JSON parse error instead of an actionable code.
    """
    settings.DEBUG = False
    response = client.get("/api/v1/core/does-not-exist/")
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "not_found"
    assert body["status"] == 404
