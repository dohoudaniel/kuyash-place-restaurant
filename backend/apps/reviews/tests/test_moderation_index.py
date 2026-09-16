"""The moderation queue's index.

`PendingReviewsView` asks for every pending review, oldest first, and names no
dish. The pre-existing composite leads on `menu_item`, so it cannot serve that
query at all — the queue was a scan of every review ever written.
"""

from __future__ import annotations

import pytest
from django.db import connection

from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


def test_the_queue_has_an_index_that_does_not_need_a_dish() -> None:
    declared = {tuple(index.fields) for index in Review._meta.indexes}
    assert ("status", "created_at") in declared
    # The per-dish one is still there: it serves the public review list.
    assert ("menu_item", "status", "-created_at") in declared


def test_the_index_reached_the_database(db) -> None:  # type: ignore[no-untyped-def]
    """Declared in Meta is not the same as applied by a migration."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Review._meta.db_table)
    assert any(
        entry["index"] and entry["columns"] == ["status", "created_at"]
        for entry in constraints.values()
    )
