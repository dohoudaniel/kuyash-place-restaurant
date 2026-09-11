"""Account signal receivers."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Profile, User


@receiver(post_save, sender=User, dispatch_uid="accounts.create_profile")
def create_profile(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Every user has a profile from the moment they exist."""
    if created:
        Profile.objects.get_or_create(user=instance)
