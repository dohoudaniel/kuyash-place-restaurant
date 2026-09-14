"""Who may watch what. The same rules as the REST endpoints, applied to a socket."""

from __future__ import annotations

from typing import Any

from django.utils.crypto import constant_time_compare

from apps.common.permissions import GROUP_KITCHEN, GROUP_MANAGERS, in_group

#: Staff who may follow any order — as `_may_read` allows over HTTP.
ORDER_STAFF_GROUPS = ("managers", "kitchen", "riders")


def may_watch_order(user: Any, order: Any, token: str = "") -> bool:
    if user is not None and getattr(user, "is_authenticated", False):
        if order.user_id and order.user_id == user.pk:
            return True
        if user.is_staff or in_group(user, *ORDER_STAFF_GROUPS):
            return True
    return (
        bool(order.guest_token) and bool(token) and constant_time_compare(order.guest_token, token)
    )


def may_watch_kitchen(user: Any) -> bool:
    return bool(user is not None and getattr(user, "is_authenticated", False)) and (
        user.is_superuser or in_group(user, GROUP_KITCHEN, GROUP_MANAGERS)
    )
