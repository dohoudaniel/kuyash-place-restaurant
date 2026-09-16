"""Fill the indexed area table from the JSON lists already on each zone.

``DeliveryZone.areas`` stays the thing staff edit; ``DeliveryArea`` is its
indexed mirror, kept in step by ``DeliveryZone.save()``. This seeds it for the
zones that existed before the mirror did.

``normalise`` is duplicated here rather than imported from ``models``: a
migration must keep behaving the way it did on the day it was written, however
the application changes afterwards.
"""

from __future__ import annotations

import re

from django.db import migrations

_NOT_WORD = re.compile(r"[^0-9a-z]+")


def normalise(text):  # type: ignore[no-untyped-def]
    return _NOT_WORD.sub(" ", str(text).lower()).strip()


def populate(apps, schema_editor):  # type: ignore[no-untyped-def]
    DeliveryZone = apps.get_model("delivery", "DeliveryZone")
    DeliveryArea = apps.get_model("delivery", "DeliveryArea")

    rows = []
    for zone in DeliveryZone.objects.all():
        seen: set[str] = set()
        for raw in zone.areas or []:
            name = str(raw).strip()
            key = normalise(name)
            if key and key not in seen:
                seen.add(key)
                rows.append(DeliveryArea(zone=zone, name=name, normalised=key))
    if rows:
        DeliveryArea.objects.bulk_create(rows, ignore_conflicts=True)


def clear(apps, schema_editor):  # type: ignore[no-untyped-def]
    apps.get_model("delivery", "DeliveryArea").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("delivery", "0004_alter_deliveryzone_areas_deliveryarea")]

    operations = [migrations.RunPython(populate, clear)]
