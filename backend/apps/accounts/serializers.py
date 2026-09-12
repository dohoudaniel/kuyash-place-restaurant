"""Account serializers."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Address, Profile, User
from apps.delivery.serializers import DeliveryZoneSerializer


class CurrentUserSerializer(serializers.ModelSerializer):
    """The payload behind ``GET /auth/session/``.

    This is the concept the frontend does not have at all today: there is no
    ``isAuthenticated`` anywhere in the codebase.
    """

    groups = serializers.SerializerMethodField()
    marketing_opt_in = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_email_verified",
            "groups",
            "marketing_opt_in",
        )
        read_only_fields = fields

    def get_groups(self, obj: User) -> list[str]:
        return sorted(group.name for group in obj.groups.all())

    def get_marketing_opt_in(self, obj: User) -> bool:
        profile = getattr(obj, "profile", None)
        return bool(profile and profile.marketing_opt_in)


class SessionSerializer(serializers.Serializer):
    """Envelope so an anonymous visitor gets ``{"user": null}`` rather than a 401."""

    user = CurrentUserSerializer(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        user = instance.get("user")
        return {"user": CurrentUserSerializer(user).data if user else None}


class RegisterSerializer(serializers.Serializer):
    """Mirrors the fields the frontend's signup form already collects."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10, trim_whitespace=False)
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    accept_terms = serializers.BooleanField()
    marketing_opt_in = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value: str) -> str:
        normalised = value.lower().strip()
        if User.objects.filter(email=normalised).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalised

    def validate_accept_terms(self, value: bool) -> bool:
        # Validated server-side. The current UI enforces this with an alert(),
        # which is trivially bypassed and legally worthless.
        if not value:
            raise serializers.ValidationError("You must accept the terms to create an account.")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class EmailOnlySerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    key = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=10, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=10, trim_whitespace=False)


class ProfileSerializer(serializers.ModelSerializer):
    """Read/write profile.

    ``email`` is deliberately read-only. Changing it must re-verify the new
    address and notify the old one (AS-5); until that flow exists in Phase 2,
    the safe behaviour is to refuse the change rather than allow an unverified one.
    """

    date_of_birth = serializers.DateField(
        source="profile.date_of_birth", allow_null=True, required=False
    )
    marketing_opt_in = serializers.BooleanField(source="profile.marketing_opt_in", required=False)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_email_verified",
            "date_of_birth",
            "marketing_opt_in",
            "date_joined",
        )
        read_only_fields = ("id", "email", "is_email_verified", "date_joined")

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        profile_data = validated_data.pop("profile", {})
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if profile_data:
            profile, _ = Profile.objects.get_or_create(user=instance)
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        return instance


class AddressSerializer(serializers.ModelSerializer):
    """A saved address, with its resolved delivery zone.

    ``zone: null`` means the address falls outside the delivery area — the UI
    must offer pickup rather than letting the customer fail at checkout.
    """

    zone = DeliveryZoneSerializer(read_only=True)
    is_deliverable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Address
        fields = (
            "id",
            "label",
            "recipient_name",
            "phone",
            "street",
            "area",
            "city",
            "state",
            "landmark",
            "delivery_notes",
            "is_default",
            "zone",
            "is_deliverable",
            "created_at",
        )
        read_only_fields = ("id", "zone", "is_deliverable", "created_at")


__all__ = [
    "AddressSerializer",
    "CurrentUserSerializer",
    "EmailOnlySerializer",
    "LoginSerializer",
    "PasswordChangeSerializer",
    "PasswordResetConfirmSerializer",
    "ProfileSerializer",
    "RegisterSerializer",
    "SessionSerializer",
    "VerifyEmailSerializer",
]
