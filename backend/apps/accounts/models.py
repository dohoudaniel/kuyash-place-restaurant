"""User and profile models."""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.common.fields import PhoneField
from apps.common.models import TimeStampedModel


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


class AddressLabel(models.TextChoices):
    HOME = "home", "Home"
    WORK = "work", "Work"
    OTHER = "other", "Other"


class Address(TimeStampedModel):
    """A saved delivery address.

    Replaces the two hardcoded Lagos addresses every visitor currently sees in
    ``AddressesSection.tsx``.

    ``landmark`` exists because Lagos addressing frequently needs it and the
    current form has no such field — riders resort to phoning.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=10, choices=AddressLabel.choices, default=AddressLabel.HOME)

    recipient_name = models.CharField(max_length=150)
    phone = PhoneField()
    street = models.CharField(max_length=255)
    area = models.CharField(
        max_length=120,
        blank=True,
        help_text="District or neighbourhood, e.g. Victoria Island. Used to resolve the zone.",
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    landmark = models.CharField(max_length=255, blank=True)
    delivery_notes = models.TextField(blank=True)

    zone = models.ForeignKey(
        "delivery.DeliveryZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="addresses",
        help_text="Resolved automatically on save. Blank means outside the delivery area.",
    )
    zone_overridden = models.BooleanField(
        default=False,
        help_text=(
            "Set when staff pick the zone by hand; automatic resolution then leaves it alone."
        ),
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.label}: {self.street}, {self.city}"

    def resolve_zone(self) -> None:
        """Match this address to a delivery zone.

        A hand-picked zone is never overwritten: staff correcting a bad match
        should not have their correction undone by the next save.
        """
        if self.zone_overridden:
            return
        from apps.core.selectors import get_current_branch
        from apps.delivery.selectors import resolve_zone

        try:
            branch = get_current_branch()
        except Exception:
            return
        self.zone = resolve_zone(branch, city=self.city, area=self.area, street=self.street)

    def save(self, *args: object, **kwargs: object) -> None:
        self.resolve_zone()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @property
    def is_deliverable(self) -> bool:
        return self.zone is not None
