"""Give order lines a public id.

Order lines use sequential integer keys, which must never reach a client
(ARCHITECTURE.md §7). Reviews target a line, so lines need an opaque id. Added
nullable, filled row by row (a column default would give every existing row the
same UUID), then made unique.
"""

import uuid

from django.db import migrations, models


def fill_public_ids(apps, schema_editor):  # type: ignore[no-untyped-def]
    OrderItem = apps.get_model("orders", "OrderItem")
    for line in OrderItem.objects.filter(public_id__isnull=True).only("pk").iterator():
        OrderItem.objects.filter(pk=line.pk).update(public_id=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="public_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(fill_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="orderitem",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
