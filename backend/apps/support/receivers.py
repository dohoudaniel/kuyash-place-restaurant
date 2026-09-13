"""Signal receivers for support."""

from __future__ import annotations

from typing import Any

from django.dispatch import receiver

from apps.accounts.signals import user_anonymised


@receiver(user_anonymised, dispatch_uid="support.erase_chats_on_anonymise")
def erase_chats_on_anonymise(sender: Any, user: Any, **kwargs: Any) -> None:
    """Chat transcripts are personal data. Tickets are kept — they are the
    record of what was asked and answered — but their transcripts live there,
    not here."""
    from apps.support.models import ChatSession

    ChatSession.objects.filter(user=user).delete()
