"""Account signal receivers and domain events."""

from __future__ import annotations

from typing import Any

import django.dispatch
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Profile, User

#: Emitted once a user's email address is confirmed.
#: Phase 1D connects order claiming here — ``orders`` never imports ``accounts``.
email_verified = django.dispatch.Signal()

#: Emitted when a user exercises their right to erasure (NDPR).
#: Listeners must scrub their own personal data and keep financial records.
user_anonymised = django.dispatch.Signal()


@receiver(post_save, sender=User, dispatch_uid="accounts.create_profile")
def create_profile(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Every user has a profile from the moment they exist."""
    if created:
        Profile.objects.get_or_create(user=instance)
