"""The menu search index, and the category list's cache.

Search used to build a ``SearchVector`` at query time and rank every row — a
scan of the whole menu per search — with an ``icontains`` fallback ORed in that
no index could ever serve.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalog.models import MenuItem

pytestmark = pytest.mark.django_db

#: The stored-vector path only exists on Postgres; SQLite has no tsvector
#: (ADR-015). These run in the Postgres CI job.
requires_postgres = pytest.mark.skipif(
    not settings.USING_POSTGRES,
    reason="needs Postgres full-text search; SQLite has no tsvector (ADR-015)",
)


def items_url() -> str:
    return reverse("v1:catalog:items")


def slugs(api_client, **params) -> list[str]:  # type: ignore[no-untyped-def]
    return [row["slug"] for row in api_client.get(items_url(), params).json()["results"]]


# ── The stored vector ─────────────────────────────────────────────────────────


def test_the_model_carries_a_stored_search_vector() -> None:
    field = MenuItem._meta.get_field("search_vector")
    assert field.null is True
    assert field.editable is False


def test_search_still_finds_the_name_and_the_description(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    """Same behaviour on both backends — the index changes the cost, not the answer."""
    assert slugs(api_client, search="smash") == [menu_item.slug]
    assert slugs(api_client, search="pickles") == [menu_item.slug]
    assert slugs(api_client, search="zzzznothing") == []


@requires_postgres
def test_saving_an_item_fills_its_search_vector(menu_item) -> None:  # type: ignore[no-untyped-def]
    menu_item.refresh_from_db()
    assert menu_item.search_vector is not None


@requires_postgres
def test_renaming_an_item_updates_its_search_vector(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    """A stored column is only as good as whatever keeps it current."""
    menu_item.name = "Tamarind Glazed Wings"
    menu_item.save()
    assert slugs(api_client, search="tamarind") == [menu_item.slug]
    assert slugs(api_client, search="smash") == []


@requires_postgres
def test_a_gin_index_covers_the_search_vector(db) -> None:  # type: ignore[no-untyped-def]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexdef FROM pg_indexes WHERE tablename = %s", [MenuItem._meta.db_table]
        )
        definitions = [row[0].lower() for row in cursor.fetchall()]
    assert any("using gin" in row and "search_vector" in row for row in definitions)


# ── The category list ─────────────────────────────────────────────────────────


def test_the_category_list_is_cached_but_follows_the_menu(  # type: ignore[no-untyped-def]
    api_client, branch, category, menu_item
) -> None:
    """The counts are what go stale: adding a dish moves a number on the page."""
    url = reverse("v1:catalog:categories")
    assert api_client.get(url).json()[0]["item_count"] == 1

    second = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Chicken Shawarma",
        slug="chicken-shawarma",
        base_price=650_000,
        needs_repricing=False,
    )
    assert api_client.get(url).json()[0]["item_count"] == 2

    second.is_active = False
    second.save()
    assert api_client.get(url).json()[0]["item_count"] == 1


def test_a_warm_category_list_costs_nothing(api_client, branch, category, menu_item) -> None:  # type: ignore[no-untyped-def]
    url = reverse("v1:catalog:categories")
    api_client.get(url)
    with CaptureQueriesContext(connection) as warm:
        assert api_client.get(url).status_code == 200
    assert len(warm) == 0


@pytest.mark.parametrize(
    "name",
    ["v1:catalog:items", "v1:catalog:categories", "v1:catalog:featured", "v1:catalog:dietary-tags"],
)
def test_the_menu_tells_caches_it_may_be_cached(api_client, branch, name) -> None:  # type: ignore[no-untyped-def]
    header = api_client.get(reverse(name))["Cache-Control"]
    assert "public" in header and "max-age=" in header
