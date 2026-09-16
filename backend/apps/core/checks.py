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

from django.conf import settings
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


#: Cache backends that are private to one worker process.
PER_PROCESS_CACHE_BACKENDS = ("locmem", "dummy", "filebased")


@register("kuyash", deploy=True)
def check_proxy_count_behind_a_proxy(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Behind a load balancer, a proxy count of 0 puts every visitor on one IP.

    This is the launch-day landmine: ``anon: 100/min`` becomes a hundred requests
    a minute for the entire site, and ``order_create: 10/hour`` becomes **ten
    orders an hour, in total**. It is an Error, not a Warning, because the site
    looks healthy while refusing almost everybody — there is no symptom to
    notice and no gradual degradation to catch it.

    Trusting a proxy for HTTPS (``SECURE_PROXY_SSL_HEADER``) is the giveaway that
    a proxy is in front of Django, so the two settings must agree.
    """
    if settings.SECURE_PROXY_SSL_HEADER and settings.TRUSTED_PROXY_COUNT <= 0:
        return [
            Error(
                "Django trusts a proxy for HTTPS but TRUSTED_PROXY_COUNT is 0.",
                hint=(
                    "Every request would appear to come from the proxy, so the whole site "
                    "shares one throttle bucket: ten orders per hour, site-wide. Set "
                    "TRUSTED_PROXY_COUNT to the number of proxies in front of Django "
                    "(usually 1). See apps/common/client_ip.py and SECURITY.md §8."
                ),
                id="kuyash.E021",
            )
        ]
    return []


@register("kuyash", deploy=True)
def check_cache_is_shared(app_configs: Any, **kwargs: Any) -> list[Any]:
    """A per-process cache is not a cache, it is N caches that disagree.

    Throttle counters multiply by the number of workers — ``5/min`` across eight
    processes is forty attempts a minute — and idempotency breaks outright: the
    claim a second request must see was written into a different process's
    memory, so a double-tapped Confirm Order places two orders.
    """
    if settings.DEBUG:
        return []
    backend = str(settings.CACHES.get("default", {}).get("BACKEND", "")).lower()
    if any(name in backend for name in PER_PROCESS_CACHE_BACKENDS):
        return [
            Error(
                "The default cache is not shared between processes.",
                hint=(
                    "Throttles would multiply by worker count and idempotency would stop "
                    "working, so a double-tapped Confirm Order could place two orders. "
                    "Set REDIS_URL so CACHES uses django.core.cache.backends.redis.RedisCache."
                ),
                id="kuyash.E022",
            )
        ]
    return []
