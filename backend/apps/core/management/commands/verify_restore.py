"""Prove a restored database is usable, not merely present (DEPLOYMENT.md §8).

A restore "succeeds" as soon as ``pg_restore`` exits 0 — including a dump from
the wrong day, a dump missing a migration, or one taken with a different
``SECRET_KEY`` so no staff member can pass two-factor. This command checks what
the business depends on:

* every migration in the code is applied;
* every order's stored total still adds up from its own parts;
* every order's lines add up to its subtotal;
* every card or transfer order marked paid has a successful payment record;
* every loyalty balance equals the sum of its ledger;
* staff authenticator secrets decrypt with this environment's ``SECRET_KEY``;
* optionally, the newest data is recent enough (``--max-age-hours``).

Exits non-zero on any failure, so ``scripts/restore-drill.sh`` and CI can rely on
it. Read-only: it never writes to the database.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Max, Sum
from django.utils import timezone

SAMPLE = 5


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    examples: list[str] = field(default_factory=list)
    warning_only: bool = False


class Command(BaseCommand):
    help = "Check that a restored database is complete and internally consistent."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--max-age-hours",
            type=float,
            default=None,
            help="Fail if the newest order or sign-up is older than this (a stale dump).",
        )
        parser.add_argument("--json", action="store_true", help="Print the report as JSON.")

    def handle(self, *args: Any, **options: Any) -> None:
        checks = [
            self.migrations(),
            self.order_totals(),
            self.order_lines(),
            self.paid_orders_have_payments(),
            self.loyalty_balances(),
            self.staff_mfa_secrets(),
        ]
        if options["max_age_hours"] is not None:
            checks.append(self.freshness(options["max_age_hours"]))

        failures = [check for check in checks if not check.ok and not check.warning_only]
        counts = self.counts()
        report = {"ok": not failures, "counts": counts, "checks": [asdict(c) for c in checks]}

        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            for name, count in counts.items():
                self.stdout.write(f"  {name:<22} {count}")
            for check in checks:
                mark = "✓" if check.ok else ("!" if check.warning_only else "✗")
                self.stdout.write(f"{mark} {check.name}: {check.detail}")
                for example in check.examples:
                    self.stdout.write(f"    - {example}")

        if failures:
            raise CommandError(
                f"Restore verification failed: {', '.join(c.name for c in failures)}"
            )
        if not options["json"]:
            self.stdout.write(self.style.SUCCESS("Restore verified."))

    # ── Checks ────────────────────────────────────────────────────────────────

    @staticmethod
    def counts() -> dict[str, int]:
        from apps.accounts.models import User
        from apps.catalog.models import MenuItem
        from apps.loyalty.models import PointsLedgerEntry
        from apps.orders.models import Order
        from apps.payments.models import PaymentTransaction
        from apps.reservations.models import Reservation

        return {
            "users": User.objects.count(),
            "menu_items": MenuItem.all_objects.count()
            if hasattr(MenuItem, "all_objects")
            else MenuItem.objects.count(),
            "orders": Order.objects.count(),
            "payment_transactions": PaymentTransaction.objects.count(),
            "reservations": Reservation.objects.count(),
            "loyalty_entries": PointsLedgerEntry.objects.count(),
        }

    @staticmethod
    def migrations() -> Check:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        pending = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]
        if pending:
            return Check(
                "migrations",
                False,
                f"{len(pending)} migration(s) in the code are not in this database — "
                "the dump is older than the release, or the restore was partial",
                pending[:SAMPLE],
            )
        return Check("migrations", True, "all applied")

    @staticmethod
    def order_totals() -> Check:
        from apps.orders.models import Order

        wrong: list[str] = []
        fields = (
            "reference",
            "subtotal",
            "discount_total",
            "delivery_fee",
            "service_charge",
            "vat_total",
            "tip",
            "grand_total",
            "prices_included_vat",
        )
        for row in Order.objects.values(*fields).iterator():
            vat = 0 if row["prices_included_vat"] else row["vat_total"]
            expected = max(
                row["subtotal"]
                - row["discount_total"]
                + row["delivery_fee"]
                + row["service_charge"]
                + vat
                + row["tip"],
                0,
            )
            if expected != row["grand_total"]:
                wrong.append(
                    f"{row['reference']}: stored {row['grand_total']}, parts give {expected}"
                )
        if wrong:
            return Check(
                "order_totals", False, f"{len(wrong)} order total(s) do not add up", wrong[:SAMPLE]
            )
        return Check("order_totals", True, "every total adds up")

    @staticmethod
    def order_lines() -> Check:
        from apps.orders.models import Order

        wrong = [
            f"{row['reference']}: lines {row['lines']}, subtotal {row['subtotal']}"
            for row in Order.objects.annotate(lines=Sum("items__line_subtotal"))
            .filter(lines__isnull=False)
            .values("reference", "lines", "subtotal")
            .iterator()
            if row["lines"] != row["subtotal"]
        ]
        if wrong:
            return Check(
                "order_lines",
                False,
                f"{len(wrong)} order(s) have lines that do not match the subtotal — "
                "order items are missing or duplicated",
                wrong[:SAMPLE],
            )
        return Check("order_lines", True, "every order's lines match its subtotal")

    @staticmethod
    def paid_orders_have_payments() -> Check:
        from apps.orders.models import Order, PaymentMethod, PaymentStatus
        from apps.payments.models import TransactionStatus

        missing = list(
            Order.objects.filter(
                payment_method__in=[PaymentMethod.CARD, PaymentMethod.TRANSFER],
                payment_status__in=[
                    PaymentStatus.PAID,
                    PaymentStatus.PARTIALLY_REFUNDED,
                    PaymentStatus.REFUNDED,
                ],
            )
            .exclude(transactions__status=TransactionStatus.SUCCESS)
            .values_list("reference", flat=True)
            .distinct()
        )
        if missing:
            return Check(
                "paid_orders",
                False,
                f"{len(missing)} paid order(s) have no successful payment record",
                missing[:SAMPLE],
            )
        return Check("paid_orders", True, "every paid card or transfer order has its payment")

    @staticmethod
    def loyalty_balances() -> Check:
        from apps.loyalty.models import LoyaltyAccount

        wrong = [
            f"account {row['pk']}: balance {row['points_balance']}, ledger {row['ledger'] or 0}"
            for row in LoyaltyAccount.objects.annotate(ledger=Sum("entries__points"))
            .values("pk", "points_balance", "ledger")
            .iterator()
            if (row["ledger"] or 0) != row["points_balance"]
        ]
        if wrong:
            return Check(
                "loyalty_balances",
                False,
                f"{len(wrong)} loyalty balance(s) differ from their ledger",
                wrong[:SAMPLE],
            )
        return Check("loyalty_balances", True, "every balance equals its ledger")

    @staticmethod
    def staff_mfa_secrets() -> Check:
        from allauth.mfa.models import Authenticator
        from cryptography.fernet import InvalidToken

        from apps.accounts.mfa_adapter import KuyashMFAAdapter

        adapter = KuyashMFAAdapter()
        unreadable = []
        for authenticator in Authenticator.objects.filter(
            type=Authenticator.Type.TOTP
        ).select_related("user"):
            try:
                adapter.decrypt(authenticator.data.get("secret", ""))
            except (InvalidToken, ValueError, TypeError):
                unreadable.append(authenticator.user.email)
        if unreadable:
            return Check(
                "staff_mfa_secrets",
                False,
                f"{len(unreadable)} staff authenticator(s) cannot be read with this SECRET_KEY — "
                "those staff must re-enrol, or restore with the original key",
                unreadable[:SAMPLE],
                warning_only=True,
            )
        return Check("staff_mfa_secrets", True, "staff two-factor secrets readable")

    @staticmethod
    def freshness(max_age_hours: float) -> Check:
        from apps.accounts.models import User
        from apps.orders.models import Order

        newest = max(
            (
                moment
                for moment in (
                    Order.objects.aggregate(latest=Max("created_at"))["latest"],
                    User.objects.aggregate(latest=Max("date_joined"))["latest"],
                )
                if moment is not None
            ),
            default=None,
        )
        if newest is None:
            return Check(
                "freshness", False, "no orders or sign-ups at all — is this the right dump?"
            )
        age = timezone.now() - newest
        hours = age / timedelta(hours=1)
        if hours > max_age_hours:
            return Check(
                "freshness",
                False,
                f"newest data is {hours:.1f} h old (limit {max_age_hours:g} h) — a stale dump",
            )
        return Check("freshness", True, f"newest data is {hours:.1f} h old")
