"""Account serializers."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    """The payload behind ``GET /auth/session/``.

    This is the concept the frontend currently does not have at all: there is no
    ``isAuthenticated`` anywhere in the codebase today.
    """

    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone", "is_email_verified", "groups")
        read_only_fields = fields

    def get_groups(self, obj: User) -> list[str]:
        return sorted(group.name for group in obj.groups.all())


class SessionSerializer(serializers.Serializer):
    """Envelope so an anonymous visitor gets ``{"user": null}`` rather than a 401."""

    user = CurrentUserSerializer(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        user = instance.get("user")
        return {"user": CurrentUserSerializer(user).data if user else None}
