"""Seed the baseline data the system needs to run.

Idempotent: safe to run repeatedly. Phase 1A extends this with categories and
the 18 menu items (each flagged ``needs_repricing``); see docs/DATA_MODEL.md §19.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.common.permissions import ALL_GROUPS
from apps.core.models import Branch, OpeningHours, Service, SiteSettings, Weekday

BRANCH_DEFAULTS: dict[str, Any] = {
    "name": "Kuyash Place — Victoria Island",
    "slug": "victoria-island",
    "phone": "+2348000000000",
    "email": "hello@kuyashplace.com",
    "address_line": "123 Gourmet Street, Victoria Island",
    "city": "Lagos",
    "state": "Lagos",
    "timezone": "Africa/Lagos",
    "currency": "NGN",
    "prices_include_vat": True,
    "vat_rate_bps": 750,
    "is_accepting_orders": True,
    # Placeholders — the owner sets real values before launch (docs/ROADMAP.md Gate 1).
    "min_order_value": 200_000,  # ₦2,000.00
    "free_delivery_threshold": 1_500_000,  # ₦15,000.00
    "default_prep_minutes": 25,
}

WEEKLY_HOURS = [
    (Weekday.MONDAY, dt.time(11, 0), dt.time(22, 0)),
    (Weekday.TUESDAY, dt.time(11, 0), dt.time(22, 0)),
    (Weekday.WEDNESDAY, dt.time(11, 0), dt.time(22, 0)),
    (Weekday.THURSDAY, dt.time(11, 0), dt.time(22, 0)),
    (Weekday.FRIDAY, dt.time(11, 0), dt.time(23, 0)),
    (Weekday.SATURDAY, dt.time(10, 0), dt.time(23, 0)),
    (Weekday.SUNDAY, dt.time(12, 0), dt.time(21, 0)),
]


class Command(BaseCommand):
    help = "Create the baseline branch, opening hours, site settings and role groups."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--reset-hours",
            action="store_true",
            help="Replace existing opening hours with the defaults.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        branch, created = Branch.objects.get_or_create(
            slug=BRANCH_DEFAULTS["slug"], defaults=BRANCH_DEFAULTS
        )
        self._report("Branch", branch.name, created)

        if options["reset_hours"]:
            branch.opening_hours.all().delete()

        for weekday, opens_at, closes_at in WEEKLY_HOURS:
            _, made = OpeningHours.objects.get_or_create(
                branch=branch,
                weekday=weekday,
                service=Service.ALL_DAY,
                defaults={"opens_at": opens_at, "closes_at": closes_at},
            )
            if made:
                self.stdout.write(f"  + hours {Weekday(weekday).label}")

        settings_obj = SiteSettings.load()
        if not settings_obj.tagline:
            settings_obj.tagline = "Tastefully Classy"
            settings_obj.support_email = "hello@kuyashplace.com"
            settings_obj.orders_email = "orders@kuyashplace.com"
            settings_obj.save()
        self._report("SiteSettings", settings_obj.site_name, False)

        for name in ALL_GROUPS:
            _, made = Group.objects.get_or_create(name=name)
            self._report("Group", name, made)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write(
            self.style.WARNING(
                "Reminder: min_order_value and free_delivery_threshold are PLACEHOLDERS. "
                "Set real values in the admin before launch (docs/ROADMAP.md Gate 1)."
            )
        )

    def _report(self, kind: str, label: str, created: bool) -> None:
        verb = self.style.SUCCESS("created") if created else self.style.NOTICE("exists")
        self.stdout.write(f"{kind:<14} {label:<40} {verb}")
