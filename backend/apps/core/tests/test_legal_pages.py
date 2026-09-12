"""Legal pages: versioning, publication, and the tax-copy gate.

The gate is the point of this module. `app/terms/page.tsx:47` promised
tax-inclusive pricing while `CartSummary.tsx:23` added 7.5% on top, and nothing
in the system could notice. These tests are what notices.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.checks import (
    check_legal_copy_matches_tax_policy,
    check_legal_pages_are_published,
)
from apps.core.legal_seed import _pricing_clause, seed_legal_pages
from apps.core.models import Branch, LegalPage

pytestmark = pytest.mark.django_db


def ids(issues: list) -> list[str]:
    return [issue.id for issue in issues]


@pytest.fixture
def seeded(branch: Branch) -> Branch:
    seed_legal_pages(branch)
    return branch


# ──────────────────────────────────────────────────────────────────────────────
# Versioning
# ──────────────────────────────────────────────────────────────────────────────


def test_current_returns_the_highest_effective_version(branch: Branch) -> None:
    LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms",
        body="v1",
        published=True,
        effective_from=dt.date(2026, 1, 1),
    )
    newer = LegalPage.objects.create(
        slug="terms",
        version=2,
        title="Terms",
        body="v2",
        published=True,
        effective_from=dt.date(2026, 6, 1),
    )
    assert LegalPage.current("terms") == newer


def test_a_future_dated_version_is_a_schedule_not_the_policy(branch: Branch) -> None:
    """A version dated next month is a planned change, not what applies today."""
    live = LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms",
        body="today",
        published=True,
        effective_from=dt.date(2026, 1, 1),
    )
    LegalPage.objects.create(
        slug="terms",
        version=2,
        title="Terms",
        body="later",
        published=True,
        effective_from=dt.date(2099, 1, 1),
    )
    assert LegalPage.current("terms") == live
    assert LegalPage.current("terms", on=dt.date(2099, 6, 1)).body == "later"


def test_an_unpublished_draft_is_never_current(branch: Branch) -> None:
    LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms",
        body="live",
        published=True,
        effective_from=dt.date(2026, 1, 1),
    )
    LegalPage.objects.create(
        slug="terms",
        version=2,
        title="Terms",
        body="draft",
        published=False,
        effective_from=dt.date(2026, 2, 1),
    )
    assert LegalPage.current("terms").body == "live"


def test_current_is_none_when_nothing_is_published(branch: Branch) -> None:
    assert LegalPage.current("terms") is None


def test_next_version_starts_at_one_and_increments(branch: Branch) -> None:
    assert LegalPage.next_version_for("terms") == 1
    LegalPage.objects.create(slug="terms", version=1, title="Terms", body="x")
    LegalPage.objects.create(slug="terms", version=2, title="Terms", body="y")
    assert LegalPage.next_version_for("terms") == 3


def test_the_same_version_cannot_be_published_twice(branch: Branch) -> None:
    from django.db import IntegrityError

    LegalPage.objects.create(slug="terms", version=1, title="Terms", body="x")
    with pytest.raises(IntegrityError):
        LegalPage.objects.create(slug="terms", version=1, title="Terms again", body="y")


def test_str_names_the_version(branch: Branch) -> None:
    page = LegalPage.objects.create(slug="terms", version=3, title="Terms", body="x")
    assert str(page) == "Terms v3"


# ──────────────────────────────────────────────────────────────────────────────
# Seeded content
# ──────────────────────────────────────────────────────────────────────────────


def test_seed_publishes_the_five_pages(seeded: Branch) -> None:
    slugs = set(LegalPage.objects.filter(published=True).values_list("slug", flat=True))
    assert slugs == {"terms", "privacy", "cookies", "refunds", "accessibility"}


def test_seeding_twice_does_not_duplicate(seeded: Branch) -> None:
    assert seed_legal_pages(seeded) == 0
    assert LegalPage.objects.count() == 5


def test_seeded_terms_state_the_vat_direction_the_branch_actually_uses(
    seeded: Branch,
) -> None:
    """The clause is generated, not asserted.

    This is the fix for the contradiction: the terms cannot claim inclusive
    pricing unless the branch actually prices inclusively, because the sentence
    is produced from that field.
    """
    body = LegalPage.current("terms").body
    assert "include VAT at 7.5%" in body
    assert "before VAT" not in body


def test_exclusive_pricing_produces_exclusive_wording(branch: Branch) -> None:
    branch.prices_include_vat = False
    branch.save(update_fields=["prices_include_vat"])
    clause = _pricing_clause(branch)
    assert "before VAT" in clause
    assert "added at checkout" in clause


def test_privacy_page_states_that_no_card_number_is_held(seeded: Branch) -> None:
    """SAQ A in prose. If this ever stops being true, the policy is a lie."""
    body = LegalPage.current("privacy").body.lower()
    assert "do not receive or store your card number" in body


# ──────────────────────────────────────────────────────────────────────────────
# The deploy gate
# ──────────────────────────────────────────────────────────────────────────────


def test_gate_passes_on_seeded_content(seeded: Branch) -> None:
    assert check_legal_copy_matches_tax_policy(None) == []
    assert check_legal_pages_are_published(None) == []


def test_gate_fails_when_the_branch_flips_to_exclusive_pricing(seeded: Branch) -> None:
    """The exact failure the frontend shipped with, now caught before deploy."""
    seeded.prices_include_vat = False
    seeded.save(update_fields=["prices_include_vat"])

    issues = check_legal_copy_matches_tax_policy(None)
    assert "kuyash.E002" in ids(issues)
    assert "terms" in issues[0].msg
    # The hint is read by whoever is deploying, so it quotes the offending
    # wording rather than the pattern that matched it.
    assert "“includes VAT”" in issues[0].hint
    assert "\\s" not in issues[0].hint


def test_gate_fails_on_the_original_frontend_wording(branch: Branch) -> None:
    """Verbatim from `app/terms/page.tsx:47`, against an exclusive-VAT branch."""
    branch.prices_include_vat = False
    branch.save(update_fields=["prices_include_vat"])
    LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms of Service",
        body="All prices are in Nigerian Naira (₦) and include applicable taxes.",
        published=True,
        effective_from=dt.date(2026, 1, 1),
    )
    assert "kuyash.E002" in ids(check_legal_copy_matches_tax_policy(None))


def test_gate_ignores_unpublished_drafts(seeded: Branch) -> None:
    """A draft is allowed to be wrong; that is what drafting is for."""
    seeded.prices_include_vat = False
    seeded.save(update_fields=["prices_include_vat"])
    LegalPage.objects.filter(published=True).update(published=False)
    assert check_legal_copy_matches_tax_policy(None) == []


def test_gate_does_not_fire_on_rewritten_but_consistent_copy(seeded: Branch) -> None:
    """Staff may reword freely; only a contradiction fails the build."""
    LegalPage.objects.filter(slug="terms").update(
        body="Every price on this menu is what you pay. Nothing is added later."
    )
    assert check_legal_copy_matches_tax_policy(None) == []


def test_gate_is_silent_without_a_branch(db) -> None:  # type: ignore[no-untyped-def]
    assert check_legal_copy_matches_tax_policy(None) == []


def test_missing_pages_warn(branch: Branch) -> None:
    issues = check_legal_pages_are_published(None)
    assert "kuyash.W003" in ids(issues)
    assert "terms" in issues[0].msg


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────


def test_list_is_public_and_names_every_page(api_client, seeded: Branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:core:legal-list"))
    assert response.status_code == 200
    assert [row["slug"] for row in response.data] == [
        "accessibility",
        "cookies",
        "privacy",
        "refunds",
        "terms",
    ]
    assert "body" not in response.data[0]


def test_list_shows_one_row_per_slug_not_one_per_version(api_client, seeded: Branch) -> None:  # type: ignore[no-untyped-def]
    LegalPage.objects.create(
        slug="terms",
        version=2,
        title="Terms of Service",
        body="v2",
        published=True,
        effective_from=timezone.localdate(),
    )
    response = api_client.get(reverse("v1:core:legal-list"))
    terms = [row for row in response.data if row["slug"] == "terms"]
    assert len(terms) == 1
    assert terms[0]["version"] == 2


def test_detail_returns_the_page_body(api_client, seeded: Branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:core:legal-detail", args=["privacy"]))
    assert response.status_code == 200
    assert response.data["title"] == "Privacy Policy"
    assert response.data["version"] == 1
    assert "Nigeria Data Protection Regulation" in response.data["body"]


def test_detail_404s_for_an_unknown_page(api_client, seeded: Branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(reverse("v1:core:legal-detail", args=["nonsense"]))
    assert response.status_code == 404


def test_detail_404s_for_a_draft(api_client, branch: Branch) -> None:  # type: ignore[no-untyped-def]
    LegalPage.objects.create(slug="terms", version=1, title="Terms", body="draft", published=False)
    response = api_client.get(reverse("v1:core:legal-detail", args=["terms"]))
    assert response.status_code == 404


def test_gate_skips_a_slug_whose_only_version_is_future_dated(branch: Branch) -> None:
    """Published but not yet in force: there is no current wording to check."""
    branch.prices_include_vat = False
    branch.save(update_fields=["prices_include_vat"])
    LegalPage.objects.create(
        slug="terms",
        version=1,
        title="Terms",
        body="All prices include VAT.",
        published=True,
        effective_from=dt.date(2099, 1, 1),
    )
    assert check_legal_copy_matches_tax_policy(None) == []


def test_checks_stay_quiet_before_the_database_is_migrated(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A fresh CI checkout runs `check` before `migrate`; it must not crash."""
    from django.db import ProgrammingError

    from apps.core import models as core_models

    def explode(*args: object, **kwargs: object) -> None:
        raise ProgrammingError("relation does not exist")

    monkeypatch.setattr(core_models.Branch.objects, "filter", explode)
    monkeypatch.setattr(core_models.LegalPage, "current", staticmethod(explode))

    assert check_legal_copy_matches_tax_policy(None) == []
    assert check_legal_pages_are_published(None) == []
