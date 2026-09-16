"""Catalogue read queries.

All filtering and sorting happens here, server-side. The frontend currently
filters in the browser and two of its five sort options are literally
``return 0``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db.models import F, Q, QuerySet

from apps.catalog.models import SEARCH_CONFIG, Category, MenuItem

SORT_OPTIONS = {
    "popular": ("-order_count", "display_order", "name"),
    "price_asc": ("base_price", "name"),
    "price_desc": ("-base_price", "name"),
    "rating": (None, "display_order", "name"),  # rating handled specially (nulls last)
    "newest": (None, "name"),  # newest handled specially (nulls last)
    "default": ("display_order", "name"),
}


def base_queryset() -> QuerySet[MenuItem]:
    """Public catalogue: active, priced, with related data prefetched."""
    return (
        MenuItem.objects.orderable()
        .select_related("category", "branch")
        .prefetch_related(
            "images",
            "dietary_tags",
            "variants",
            "availability_windows",
            "modifier_groups__modifiers",
        )
    )


def _apply_search(queryset: QuerySet[MenuItem], term: str) -> QuerySet[MenuItem]:
    """Full-text search on Postgres, substring matching elsewhere.

    On Postgres this matches against the **stored** ``search_vector`` column,
    which the GIN index in migration 0003 covers. It used to build a
    ``SearchVector`` from ``name`` and ``description`` at query time and rank
    every row — a sequential scan of the whole menu per search — and then OR in
    a ``name__icontains``, which no index can ever serve and which quietly made
    the scan mandatory even when the full-text half matched nothing.

    Local development runs on SQLite (ADR-015), which has no ``tsvector``, so
    the behaviour degrades to substring matching rather than crashing.
    """
    term = term.strip()
    if not term:
        return queryset

    if settings.USING_POSTGRES:  # pragma: no cover - exercised in Postgres CI
        from django.contrib.postgres.search import SearchQuery, SearchRank

        query = SearchQuery(term, search_type="websearch", config=SEARCH_CONFIG)
        return (
            queryset.filter(search_vector=query)
            .annotate(rank=SearchRank(F("search_vector"), query))
            .order_by("-rank", "display_order", "name")
        )

    return queryset.filter(Q(name__icontains=term) | Q(description__icontains=term))


def filter_items(
    *,
    category: str = "",
    search: str = "",
    dietary: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_rating: Decimal | None = None,
    available_only: bool = False,
    featured_only: bool = False,
    sort: str = "default",
) -> QuerySet[MenuItem]:
    """Apply the public catalogue filters.

    Every parameter is optional; an empty call returns the whole live menu.
    """
    queryset = base_queryset()

    if category:
        queryset = queryset.filter(category__slug=category)

    if dietary:
        # AND semantics: "vegan,gluten-free" means both, not either.
        for slug in dietary:
            queryset = queryset.filter(dietary_tags__slug=slug)
        queryset = queryset.distinct()

    if min_price is not None:
        queryset = queryset.filter(base_price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(base_price__lte=max_price)

    if min_rating is not None:
        queryset = queryset.filter(average_rating__gte=min_rating)

    if featured_only:
        queryset = queryset.filter(is_featured=True)

    if available_only:
        queryset = (
            MenuItem.objects.available_now()
            .filter(pk__in=queryset.values("pk"))
            .select_related("category", "branch")
            .prefetch_related(
                "images",
                "dietary_tags",
                "variants",
                "availability_windows",
                "modifier_groups__modifiers",
            )
        )

    if search:
        queryset = _apply_search(queryset, search)
        if sort == "default":
            return queryset  # preserve relevance ordering

    return _apply_sort(queryset, sort)


def _apply_sort(queryset: QuerySet[MenuItem], sort: str) -> QuerySet[MenuItem]:
    """Order the catalogue.

    ``rating`` and ``newest`` put NULLs last explicitly: an unrated dish should
    sit below a 3-star one, not above a 5-star one.
    """
    if sort == "rating":
        return queryset.order_by(F("average_rating").desc(nulls_last=True), "display_order", "name")
    if sort == "newest":
        return queryset.order_by(F("published_at").desc(nulls_last=True), "name")

    ordering = SORT_OPTIONS.get(sort) or SORT_OPTIONS["default"]
    return queryset.order_by(*[field for field in ordering if field])


def categories_with_counts(branch: Any) -> QuerySet[Category]:
    """Active categories, each annotated with how many orderable items it holds."""
    from django.db.models import Count

    return (
        Category.objects.filter(branch=branch, is_active=True)
        .annotate(
            item_count=Count(
                "items",
                filter=Q(items__is_active=True, items__needs_repricing=False),
                distinct=True,
            )
        )
        .order_by("display_order", "name")
    )
