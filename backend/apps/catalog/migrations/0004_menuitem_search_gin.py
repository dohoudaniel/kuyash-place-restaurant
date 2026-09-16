"""The full-text index ``base.py`` promised "in Phase 1/2" and never shipped.

Postgres only. ``MenuItem.search_vector`` is a stored ``tsvector`` kept up to
date by ``MenuItem.save()``; this adds the GIN index that turns searching it
into an index lookup, and fills the column for the rows that already exist.

Before this, every menu search built a ``SearchVector`` from ``name`` and
``description`` for every row and ranked it — a sequential scan of the whole
menu, per search.

SQLite has neither ``tsvector`` nor GIN (ADR-015), so this is a no-op there and
``apps/catalog/selectors._apply_search`` falls back to substring matching. The
weights and the dictionary must match ``MenuItem.refresh_search_vector``: a
vector built with one configuration and queried with another matches nothing.
"""

from __future__ import annotations

from django.db import migrations

INDEX_NAME = "catalog_menuitem_search_gin"

CREATE_SQL = f"""
UPDATE catalog_menuitem
SET search_vector =
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B');

CREATE INDEX IF NOT EXISTS {INDEX_NAME}
    ON catalog_menuitem USING gin (search_vector);
"""

DROP_SQL = f"DROP INDEX IF EXISTS {INDEX_NAME};"


def add_index(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(CREATE_SQL)


def drop_index(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_menuitem_search_vector")]

    operations = [migrations.RunPython(add_index, drop_index)]
