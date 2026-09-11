"""Abstract base models."""

from __future__ import annotations

import uuid
from typing import Self

from django.db import models


class TimeStampedModel(models.Model):
    """UUID primary key plus creation/update timestamps.

    UUIDs rather than sequential integers so that nothing customer-facing is
    enumerable (SECURITY.md §1).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(models.Model):
    """Deactivation instead of deletion, for catalogue and content records."""

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """A model with exactly one row (site settings and similar)."""

    class Meta:
        abstract = True

    def save(self, *args: object, **kwargs: object) -> None:
        self.pk = self.__class__._default_manager.values_list("pk", flat=True).first() or self.pk
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def load(cls) -> Self:
        obj = cls._default_manager.first()
        if obj is None:
            obj = cls._default_manager.create()
        return obj
