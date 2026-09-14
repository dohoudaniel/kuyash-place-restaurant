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

from apps.catalog.models import MenuItem
from apps.catalog.seed import seed_catalogue
from apps.catering.seed import seed_catering
from apps.common.permissions import ALL_GROUPS
from apps.core.legal_seed import seed_legal_pages
from apps.core.models import Branch, OpeningHours, Service, SiteSettings, Weekday
from apps.delivery.models import DeliveryZone
from apps.promotions.models import DiscountType, PromoCode
from apps.reservations.seed import seed_reservations
from apps.support.seed import seed_faq

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

# PLACEHOLDER fees and minimums. Real values are a Gate 1 prerequisite (OD-3).
# Fees are in KOBO: ₦1,500.00 is 150_000.
DELIVERY_ZONES: list[dict[str, Any]] = [
    {
        "slug": "victoria-island",
        "name": "Victoria Island",
        "fee": 150_000,
        "min_order_value": 200_000,
        "estimated_minutes": 35,
        "areas": ["Victoria Island", "VI", "Eko Atlantic", "Adeola Odeku"],
        "display_order": 1,
    },
    {
        "slug": "ikoyi",
        "name": "Ikoyi",
        "fee": 180_000,
        "min_order_value": 200_000,
        "estimated_minutes": 40,
        "areas": ["Ikoyi", "Banana Island", "Parkview"],
        "display_order": 2,
    },
    {
        "slug": "lekki-phase-1",
        "name": "Lekki Phase 1",
        "fee": 250_000,
        "min_order_value": 300_000,
        "estimated_minutes": 50,
        "areas": ["Lekki", "Lekki Phase 1", "Admiralty Way"],
        "display_order": 3,
    },
]

# Carried over from frontend/lib/store/promoStore.ts, where every code and its
# rules ship in the JS bundle. The frontend values are dollar figures wearing a
# naira sign ("₦5 off orders over ₦30"), and SAVE500 has value: 5 — its own name
# and value already disagree. Converted to plausible naira here and seeded
# INACTIVE: nobody can redeem one until a human has reviewed it.
PROMO_CODES: list[dict[str, Any]] = [
    {
        "code": "WELCOME10",
        "discount_type": DiscountType.PERCENTAGE,
        "value": 1000,
        "max_discount": 100_000,
        "min_order_value": 200_000,
        "first_order_only": True,
        "usage_limit_per_user": 1,
        "description": "10% off your first order, up to ₦1,000",
    },
    {
        "code": "SAVE500",
        "discount_type": DiscountType.FIXED,
        "value": 50_000,
        "min_order_value": 300_000,
        "description": "₦500 off orders over ₦3,000",
    },
    {
        "code": "FREEDEL",
        "discount_type": DiscountType.FREE_DELIVERY,
        "value": 0,
        "min_order_value": 250_000,
        "description": "Free delivery on orders over ₦2,500",
    },
    {
        "code": "MEGA20",
        "discount_type": DiscountType.PERCENTAGE,
        "value": 2000,
        "max_discount": 200_000,
        "min_order_value": 500_000,
        "description": "20% off orders over ₦5,000, up to ₦2,000",
    },
    {
        "code": "FLAT15",
        "discount_type": DiscountType.FIXED,
        "value": 150_000,
        "min_order_value": 1_000_000,
        "description": "₦1,500 off orders over ₦10,000",
    },
]

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

        for payload in DELIVERY_ZONES:
            _, made = DeliveryZone.objects.get_or_create(
                branch=branch,
                slug=payload["slug"],
                defaults={k: v for k, v in payload.items() if k != "slug"},
            )
            self._report("DeliveryZone", payload["name"], made)

        for payload in PROMO_CODES:
            _, made = PromoCode.objects.get_or_create(
                branch=branch,
                code=payload["code"],
                defaults={
                    **{k: v for k, v in payload.items() if k != "code"},
                    # Inactive until reviewed — see the note on PROMO_CODES.
                    "is_active": False,
                },
            )
            self._report("PromoCode", payload["code"], made)

        from apps.notifications.models import EmailTemplate
        from apps.notifications.templates_data import DEFAULT_TEMPLATES

        for key, payload in DEFAULT_TEMPLATES.items():
            _, made = EmailTemplate.objects.get_or_create(
                key=key,
                defaults={
                    "description": payload["description"],
                    "subject": payload["subject"],
                    "text_body": payload["text_body"],
                    "available_context": payload["available_context"],
                },
            )
            if made:
                self.stdout.write(f"  + email template {key}")

        self.stdout.write("Legal pages:")
        seed_legal_pages(branch, stdout=self.stdout)

        self.stdout.write("Support:")
        seed_faq(branch, stdout=self.stdout)

        self.stdout.write("Catering:")
        seed_catering(branch, stdout=self.stdout)

        self.stdout.write("Reservations:")
        seed_reservations(branch, stdout=self.stdout)

        self.stdout.write("Catalogue:")
        seed_catalogue(branch, stdout=self.stdout)

        from apps.academy.seed import seed_academy

        self.stdout.write("Academy:")
        seed_academy(branch, stdout=self.stdout)

        from apps.loyalty.seed import seed_loyalty

        self.stdout.write("Loyalty:")
        seed_loyalty(branch, stdout=self.stdout)

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
        pending = MenuItem.objects.filter(is_active=True, needs_repricing=True).count()
        self.stdout.write(
            self.style.WARNING(
                "Reminder: min_order_value and free_delivery_threshold are PLACEHOLDERS. "
                "Set real values in the admin before launch (docs/ROADMAP.md Gate 1)."
            )
        )
        inactive_promos = PromoCode.objects.filter(branch=branch, is_active=False).count()
        if inactive_promos:
            self.stdout.write(
                self.style.WARNING(
                    f"{inactive_promos} promo code(s) seeded INACTIVE. Their values were "
                    "converted from the frontend's dollar figures; review each one in the "
                    "admin before enabling it."
                )
            )

        from apps.academy.models import Course

        draft_courses = Course.objects.filter(branch=branch, is_active=False).count()
        if draft_courses:
            self.stdout.write(
                self.style.WARNING(
                    f"{draft_courses} academy course(s) seeded INACTIVE. Confirm each instructor "
                    "and fee, schedule a cohort, then publish it in the admin."
                )
            )

        if pending:
            self.stdout.write(
                self.style.ERROR(
                    f"{pending} menu item(s) carry PLACEHOLDER prices carried over from the "
                    "frontend (₦14.90 for a grill plate — a dollar figure with a naira sign). "
                    "They are hidden from the public API and `check --deploy` will FAIL until "
                    "real prices are set and 'needs repricing' is cleared."
                )
            )

    def _report(self, kind: str, label: str, created: bool) -> None:
        verb = self.style.SUCCESS("created") if created else self.style.NOTICE("exists")
        self.stdout.write(f"{kind:<14} {label:<40} {verb}")
