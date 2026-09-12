"""Database-level double-booking prevention.

Postgres only. An ``ExclusionConstraint`` over ``(table, [start, end))`` refuses
an overlapping booking outright, whatever the application believes — the
guarantee Gate 2 requires.

SQLite has no equivalent (ADR-015), so this migration is a no-op there and the
application-level lock in ``services/booking.py`` is the only guard locally.
The concurrency test is skipped on SQLite and runs in the Postgres CI job.
"""

from __future__ import annotations

from django.db import migrations

CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE reservations_reservation
    ADD CONSTRAINT no_double_booked_table
    EXCLUDE USING gist (
        table_id WITH =,
        tstzrange(
            reserved_for,
            reserved_for + (duration_minutes || ' minutes')::interval,
            '[)'
        ) WITH &&
    )
    WHERE (status IN ('pending', 'confirmed', 'seated') AND table_id IS NOT NULL);
"""

DROP_SQL = """
ALTER TABLE reservations_reservation
    DROP CONSTRAINT IF EXISTS no_double_booked_table;
"""


def add_constraint(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(CREATE_SQL)


def drop_constraint(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("reservations", "0001_initial")]

    operations = [migrations.RunPython(add_constraint, drop_constraint)]
