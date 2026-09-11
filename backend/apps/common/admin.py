"""Admin helpers.

The mixins here are plain objects, not ``ModelAdmin`` subclasses, so they can be
combined with each other and with ``ModelAdmin`` without MRO surprises.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Model
from django.http import HttpRequest

from apps.common.money import format_money


class ReadOnlyTimestampsMixin:
    """Identity and timestamps are shown but never editable."""

    readonly_fields = ("id", "created_at", "updated_at")


class NoDeleteMixin:
    """Financial and audit records are never deleted through the admin.

    Orders, payments and status events are the business's books. Correcting one
    means writing a compensating record, not erasing history.
    """

    def has_delete_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False


def money_column(field_name: str, label: str = "") -> Any:
    """Build an admin column rendering integer kobo as ``₦12,500.00``.

    Stops anyone reading a raw kobo integer off an admin page and mistaking it
    for naira — the mistake that would let a ₦1,500 delivery fee look like ₦150,000.
    """

    def column(_self: Any, obj: Model) -> str:
        return format_money(getattr(obj, field_name) or 0)

    column.short_description = label or field_name.replace("_", " ").title()  # type: ignore[attr-defined]
    column.admin_order_field = field_name  # type: ignore[attr-defined]
    return column
