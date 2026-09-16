"""Cache invalidation for the catalogue.

The category list carries a count of orderable items per category, so it goes
stale when a *menu item* changes as surely as when a category does — adding a
dish, 86'ing one or clearing its repricing flag all move a number on the page.
Both models therefore drop the same cached payload.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Category, MenuItem
from apps.core import cache as core_cache


@receiver(post_save, sender=Category, dispatch_uid="catalog.cache.category_saved")
@receiver(post_delete, sender=Category, dispatch_uid="catalog.cache.category_deleted")
@receiver(post_save, sender=MenuItem, dispatch_uid="catalog.cache.item_saved")
@receiver(post_delete, sender=MenuItem, dispatch_uid="catalog.cache.item_deleted")
def drop_category_list(sender: Any, instance: Any, **kwargs: Any) -> None:
    core_cache.invalidate_prefix(core_cache.CATEGORIES_PREFIX)
