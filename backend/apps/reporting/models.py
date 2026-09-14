"""Reporting has no tables of its own; it reads orders, payments and deliveries.

``Report`` exists only so the Reports page appears in the admin index, with a
permission managers can be given.
"""

from __future__ import annotations

from django.db import models


class Report(models.Model):
    class Meta:
        managed = False
        default_permissions = ("view",)
        verbose_name = "report"
        verbose_name_plural = "reports"

    def __str__(self) -> str:
        return "Reports"
