"""Legal page admin.

The version history is a legal record, not a convenience. These tests cover the
controls that keep it one: a published version cannot be edited, cannot be
deleted, and a change is a new row rather than an overwrite.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.core.admin import LegalPageAdmin
from apps.core.models import Branch, LegalPage

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_instance() -> LegalPageAdmin:
    return LegalPageAdmin(LegalPage, AdminSite())


@pytest.fixture
def request_stub():  # type: ignore[no-untyped-def]
    return RequestFactory().get("/admin/core/legalpage/")


@pytest.fixture
def published(branch: Branch) -> LegalPage:
    return LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms of Service",
        body="Prices include VAT at 7.5%.",
        published=True,
        effective_from=dt.date(2026, 1, 1),
    )


def test_published_content_is_read_only(admin_instance, request_stub, published) -> None:  # type: ignore[no-untyped-def]
    readonly = admin_instance.get_readonly_fields(request_stub, published)
    for field in ("slug", "version", "title", "body", "effective_from"):
        assert field in readonly


def test_published_can_still_be_withdrawn(admin_instance, request_stub, published) -> None:  # type: ignore[no-untyped-def]
    """Unpublishing must stay possible — otherwise bad copy cannot be pulled."""
    assert "published" not in admin_instance.get_readonly_fields(request_stub, published)


def test_a_draft_is_editable_apart_from_its_version(admin_instance, request_stub, branch) -> None:  # type: ignore[no-untyped-def]
    draft = LegalPage.objects.create(slug="terms", version=1, title="Terms", body="x")
    readonly = admin_instance.get_readonly_fields(request_stub, draft)
    assert "body" not in readonly
    assert "version" in readonly


def test_the_add_form_has_no_frozen_fields(admin_instance, request_stub) -> None:  # type: ignore[no-untyped-def]
    assert admin_instance.get_readonly_fields(request_stub, None) == ("created_at", "updated_at")


def test_a_published_version_cannot_be_deleted(admin_instance, request_stub, published) -> None:  # type: ignore[no-untyped-def]
    assert admin_instance.has_delete_permission(request_stub, published) is False


def test_a_draft_can_be_deleted(admin_instance, request_stub, branch) -> None:  # type: ignore[no-untyped-def]
    draft = LegalPage.objects.create(slug="terms", version=1, title="Terms", body="x")
    assert admin_instance.has_delete_permission(request_stub, draft) is True
    assert admin_instance.has_delete_permission(request_stub, None) is True


def test_in_force_marks_only_the_live_version(admin_instance, published) -> None:  # type: ignore[no-untyped-def]
    superseded = published
    newer = LegalPage.objects.create(
        slug="terms",
        version=2,
        title="Terms of Service",
        body="Prices include VAT at 7.5%.",
        published=True,
        effective_from=dt.date(2026, 6, 1),
    )
    assert admin_instance.in_force(newer) is True
    assert admin_instance.in_force(superseded) is False


def test_in_force_is_false_when_nothing_is_published(admin_instance, branch) -> None:  # type: ignore[no-untyped-def]
    draft = LegalPage.objects.create(slug="terms", version=1, title="Terms", body="x")
    assert admin_instance.in_force(draft) is False


def test_drafting_a_new_version_copies_the_text_unpublished(
    admin_instance, request_stub, published
) -> None:  # type: ignore[no-untyped-def]
    messages: list[str] = []
    admin_instance.message_user = lambda req, msg, level=20: messages.append(msg)  # type: ignore[assignment]

    admin_instance.draft_new_version(request_stub, LegalPage.objects.filter(pk=published.pk))  # type: ignore[arg-type]

    draft = LegalPage.objects.get(slug="terms", version=2)
    assert draft.published is False
    assert draft.body == published.body
    assert draft.summary == ""
    assert "Drafted 1" in messages[0]

    # The version customers agreed to is untouched and still the live one.
    published.refresh_from_db()
    assert published.published is True
    assert LegalPage.current("terms") == published


def test_saving_a_new_page_over_an_existing_version_bumps_instead_of_erroring(
    admin_instance, request_stub, published
) -> None:  # type: ignore[no-untyped-def]
    fresh = LegalPage(slug="terms", version=1, title="Terms", body="rewritten")
    admin_instance.save_model(request_stub, fresh, None, change=False)
    assert fresh.version == 2
    assert LegalPage.objects.filter(slug="terms").count() == 2


def test_saving_the_first_version_keeps_it_at_one(admin_instance, request_stub, branch) -> None:  # type: ignore[no-untyped-def]
    fresh = LegalPage(slug="privacy", version=1, title="Privacy", body="x")
    admin_instance.save_model(request_stub, fresh, None, change=False)
    assert fresh.version == 1
