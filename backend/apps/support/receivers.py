"""Signal receivers for support."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.signals import user_anonymised
from apps.core import cache as core_cache
from apps.support.models import FaqEntry


@receiver(user_anonymised, dispatch_uid="support.erase_chats_on_anonymise")
def erase_chats_on_anonymise(sender: Any, user: Any, **kwargs: Any) -> None:
    """Chat transcripts are personal data. Tickets are kept — they are the
    record of what was asked and answered — but their transcripts live there,
    not here."""
    from apps.support.models import ChatSession

    ChatSession.objects.filter(user=user).delete()


@receiver(post_save, sender=FaqEntry, dispatch_uid="support.cache.faq_saved")
@receiver(post_delete, sender=FaqEntry, dispatch_uid="support.cache.faq_deleted")
def drop_faq_cache(sender: Any, instance: FaqEntry, **kwargs: Any) -> None:
    """Every filtered variant, not just the unfiltered list: an entry moving
    category changes two of them."""
    core_cache.invalidate_prefix(core_cache.FAQ_PREFIX)
