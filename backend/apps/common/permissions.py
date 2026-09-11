"""Shared permission classes.

Roles are Django groups, not a column on the user, so one person can be both a
manager and a rider on a short-staffed evening.
"""

from __future__ import annotations

from typing import Any

from django.utils.crypto import constant_time_compare
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

GROUP_CUSTOMERS = "customers"
GROUP_KITCHEN = "kitchen"
GROUP_RIDERS = "riders"
GROUP_MANAGERS = "managers"

ALL_GROUPS = (GROUP_CUSTOMERS, GROUP_KITCHEN, GROUP_RIDERS, GROUP_MANAGERS)


def in_group(user: Any, *groups: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=groups).exists()


class IsStaffMember(permissions.BasePermission):
    """Any staff role."""

    message = "Staff access is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return bool(user.is_staff or in_group(user, *ALL_GROUPS))


class IsKitchenStaff(permissions.BasePermission):
    message = "Kitchen access is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated) and (
            user.is_superuser or in_group(user, GROUP_KITCHEN, GROUP_MANAGERS)
        )


class IsManager(permissions.BasePermission):
    message = "Manager access is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated) and (
            user.is_superuser or in_group(user, GROUP_MANAGERS)
        )


class IsOwnerOrStaff(permissions.BasePermission):
    """Object-level ownership, with a guest-token escape hatch.

    Guests authenticate against a single order or reservation using an opaque
    token issued at creation. The comparison is constant-time so the token
    cannot be discovered by timing.
    """

    message = "You do not have access to this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user
        if user and user.is_authenticated:
            if user.is_staff or in_group(user, GROUP_MANAGERS):
                return True
            owner = getattr(obj, "user", None)
            if owner is not None and owner == user:
                return True

        expected = getattr(obj, "guest_token", "")
        supplied = request.headers.get("X-Guest-Token", "")
        return bool(expected) and bool(supplied) and constant_time_compare(expected, supplied)
