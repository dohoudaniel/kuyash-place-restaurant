"""Deployment checks for published policy copy.

The frontend shipped with `app/terms/page.tsx:47` and `app/help/page.tsx:120`
both promising "prices … include applicable taxes" while `CartSummary.tsx:23`
added 7.5% on top of the displayed price. Under the FCCPA 2018 that is a
misleading price representation, and it is exactly the kind of contradiction
that survives indefinitely because the copy and the arithmetic live in
different files owned by different people.

These checks make the contradiction a build failure instead.
"""

from __future__ import annotations

import re
from typing import Any

from django.core.checks import Error, Warning, register

#: Phrases that assert VAT-inclusive pricing, each with the wording to quote back.
#: The label is what an operator reads; the pattern is never shown to them.
INCLUSIVE_CLAIMS: tuple[tuple[str, str], ...] = (
    (r"include\s+(?:applicable\s+)?(?:vat|tax)", "include applicable tax"),
    (r"includes?\s+vat", "includes VAT"),
    (r"(?:vat|tax)[- ]inclusive", "tax-inclusive"),
    (r"inclusive\s+of\s+(?:vat|tax)", "inclusive of VAT"),
)

#: Phrases that assert VAT is added on top.
EXCLUSIVE_CLAIMS: tuple[tuple[str, str], ...] = (
    (r"before\s+vat", "before VAT"),
    (r"exclusive\s+of\s+(?:vat|tax)", "exclusive of VAT"),
    (r"(?:vat|tax)\s+(?:is\s+)?added", "VAT is added"),
    (r"plus\s+vat", "plus VAT"),
)

#: Pages a customer-facing restaurant is expected to publish.
EXPECTED_SLUGS = ("terms", "privacy", "refunds")


def _matches(body: str, claims: tuple[tuple[str, str], ...]) -> list[str]:
    text = body.lower()
    return [label for pattern, label in claims if re.search(pattern, text)]


@register("kuyash", deploy=True)
def check_legal_copy_matches_tax_policy(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Refuse to deploy while a published page contradicts what the cart charges.

    Deliberately looks for the *opposing* claim rather than for exact seeded
    wording: staff are expected to reword these pages, and a check that fired on
    every legitimate edit would be switched off within a week.

    Runs only under ``manage.py check --deploy``.
    """
    from django.db import OperationalError, ProgrammingError

    from apps.core.models import Branch, LegalPage

    try:
        branch = Branch.objects.filter(is_active=True).first()
        if branch is None:
            return []
        slugs = list(LegalPage.objects.filter(published=True).values_list("slug", flat=True))
    except (OperationalError, ProgrammingError):
        # Database not migrated yet (fresh CI checkout) — nothing to assert.
        return []

    contradicting = EXCLUSIVE_CLAIMS if branch.prices_include_vat else INCLUSIVE_CLAIMS
    promise = (
        f"prices include VAT at {branch.vat_rate_bps / 100:g}%"
        if branch.prices_include_vat
        else f"VAT at {branch.vat_rate_bps / 100:g}% is added at checkout"
    )

    issues: list[Any] = []
    for slug in sorted(set(slugs)):
        page = LegalPage.current(slug)
        if page is None:
            continue
        if hits := _matches(page.body, contradicting):
            quoted = ", ".join(f"“{hit}”" for hit in hits)
            issues.append(
                Error(
                    f"Published page '{slug}' v{page.version} contradicts the branch VAT policy.",
                    hint=(
                        f"The branch charges so that {promise}, but the page says {quoted}. "
                        "Publish a new version of the page, or change the VAT direction on the "
                        "branch — but not neither. See docs/PRD.md §7."
                    ),
                    id="kuyash.E002",
                )
            )
    return issues


@register("kuyash", deploy=True)
def check_legal_pages_are_published(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Warn when a policy page the footer links to has no published version."""
    from django.db import OperationalError, ProgrammingError

    from apps.core.models import LegalPage

    try:
        published = {slug for slug in EXPECTED_SLUGS if LegalPage.current(slug) is not None}
    except (OperationalError, ProgrammingError):
        return []

    if missing := [slug for slug in EXPECTED_SLUGS if slug not in published]:
        return [
            Warning(
                f"No published legal page for: {', '.join(missing)}.",
                hint=(
                    "Run `manage.py seed_data` to publish the initial versions, or write them "
                    "in the admin. A footer link to a page that 404s is worse than no link."
                ),
                id="kuyash.W003",
            )
        ]
    return []
