"""User and profile models."""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.common.fields import PhoneField


class User(AbstractBaseUser, PermissionsMixin):
    """A customer or staff member.

    Identified by email — the frontend collects no username anywhere, and one
    fewer credential is one fewer thing to reset.

    Roles are Django groups (``customers``, ``kitchen``, ``riders``,
    ``managers``), not a column here, so a manager can also ride on a
    short-staffed evening without a schema change.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            "The UI collects a single name field, not first/last. Optional at the "
            "model level because social sign-in may not supply one; the signup "
            "serializer requires it."
        ),
    )
    phone = PhoneField(
        blank=True,
        help_text="International format. Required before placing a delivery order.",
    )

    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Grants access to the Django admin.",
    )

    date_joined = models.DateTimeField(default=timezone.now, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email

    def save(self, *args: object, **kwargs: object) -> None:
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def get_full_name(self) -> str:
        return self.full_name or self.email

    def get_short_name(self) -> str:
        return (self.full_name or self.email).split(" ")[0]


class Profile(models.Model):
    """Customer preferences kept off the auth record.

    Phase 1B adds ``default_address``; Phase 1A adds ``dietary_preferences``.
    Both are deliberately absent here so Phase 0 has no forward dependencies.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Optional. Collected only to support birthday rewards.",
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    marketing_opt_in = models.BooleanField(
        default=False,
        help_text="Explicit consent, withdrawable (NDPR).",
    )
    preferred_language = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"
