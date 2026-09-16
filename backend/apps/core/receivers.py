"""Cache invalidation for core content.

Every cached read in ``apps/core/cache.py`` has a receiver here that drops it
when the row behind it changes. The TTL is the backstop; this is the mechanism.

Deletes matter as much as saves: replacing a branch's whole schedule starts with
``branch.opening_hours.all().delete()``, and registering ``post_delete`` is also
what stops Django taking its fast-delete path, which would skip the signal.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core import cache as core_cache
from apps.core.models import Branch, HolidayOverride, LegalPage, OpeningHours, SiteSettings


@receiver(post_save, sender=Branch, dispatch_uid="core.cache.branch_saved")
@receiver(post_delete, sender=Branch, dispatch_uid="core.cache.branch_deleted")
def drop_branch(sender: Any, instance: Branch, **kwargs: Any) -> None:
    core_cache.invalidate_all(
        keys=(
            core_cache.CURRENT_BRANCH_CACHE_KEY,
            core_cache.OPENING_HOURS_KEY.format(branch=instance.pk),
            core_cache.HOLIDAYS_KEY.format(branch=instance.pk),
        ),
        prefixes=(core_cache.CATEGORIES_PREFIX,),
    )


@receiver(post_save, sender=OpeningHours, dispatch_uid="core.cache.hours_saved")
@receiver(post_delete, sender=OpeningHours, dispatch_uid="core.cache.hours_deleted")
def drop_opening_hours(sender: Any, instance: OpeningHours, **kwargs: Any) -> None:
    core_cache.invalidate(core_cache.OPENING_HOURS_KEY.format(branch=instance.branch_id))


@receiver(post_save, sender=HolidayOverride, dispatch_uid="core.cache.holiday_saved")
@receiver(post_delete, sender=HolidayOverride, dispatch_uid="core.cache.holiday_deleted")
def drop_holidays(sender: Any, instance: HolidayOverride, **kwargs: Any) -> None:
    core_cache.invalidate(core_cache.HOLIDAYS_KEY.format(branch=instance.branch_id))


@receiver(post_save, sender=SiteSettings, dispatch_uid="core.cache.settings_saved")
def drop_site_settings(sender: Any, instance: SiteSettings, **kwargs: Any) -> None:
    core_cache.invalidate(core_cache.SITE_SETTINGS_KEY)


@receiver(post_save, sender=LegalPage, dispatch_uid="core.cache.legal_saved")
@receiver(post_delete, sender=LegalPage, dispatch_uid="core.cache.legal_deleted")
def drop_legal_pages(sender: Any, instance: LegalPage, **kwargs: Any) -> None:
    core_cache.invalidate(
        core_cache.LEGAL_INDEX_KEY,
        core_cache.LEGAL_PAGE_KEY.format(slug=instance.slug),
    )
