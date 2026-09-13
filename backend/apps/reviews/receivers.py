"""Signal receivers for reviews."""

from __future__ import annotations

from typing import Any

from django.dispatch import receiver

from apps.accounts.signals import user_anonymised
from apps.reviews.services import erase_reviews


@receiver(user_anonymised, dispatch_uid="reviews.erase_on_anonymise")
def erase_on_anonymise(sender: Any, user: Any, **kwargs: Any) -> None:
    """A review is personal data: its words identify the writer as surely as a name."""
    erase_reviews(user)
