"""What still stands between this environment and launch (ROADMAP.md Gate 1).

Run it in the environment being launched, with its real settings:

    python manage.py launch_status          # grouped report
    python manage.py launch_status --json   # for a dashboard or CI

Each item is one of:

* ``done`` — nothing to do;
* ``blocking`` — a project system check at error level; the command exits non-zero;
* ``todo`` — needs doing before launch, but the site will run without it;
* ``manual`` — cannot be checked from code; listed so it is not forgotten.

Read-only: it never changes anything.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.core.checks import run_checks
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

MARKS = {"done": "✓", "blocking": "✗", "todo": "!", "manual": "☐"}


@dataclass
class Item:
    area: str
    name: str
    state: str
    detail: str


class Command(BaseCommand):
    help = "Report what still stands between this environment and launch."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--json", action="store_true", help="Print the report as JSON.")

    def handle(self, *args: Any, **options: Any) -> None:
        database = self.database()
        # Staffing reads tables a pending migration may not have created yet.
        people = self.people() if database.state == "done" else []
        items = [database, *self.system_checks(), *self.operations(), *people, *self.manual()]
        blocking = [item for item in items if item.state == "blocking"]
        todo = [item for item in items if item.state == "todo"]
        ready = not blocking and not todo

        if options["json"]:
            report = {"ready": ready, "items": [asdict(item) for item in items]}
            self.stdout.write(json.dumps(report, indent=2))
        else:
            area = ""
            for item in items:
                if item.area != area:
                    area = item.area
                    self.stdout.write(f"\n{area}")
                self.stdout.write(f"  {MARKS[item.state]} {item.name}: {item.detail}")
            self.stdout.write(
                f"\n{len(blocking)} blocking, {len(todo)} to do, "
                f"{sum(item.state == 'manual' for item in items)} to confirm by hand."
            )

        if blocking:
            raise CommandError(f"{len(blocking)} blocking item(s) before launch.")
        if ready and not options["json"]:
            self.stdout.write(self.style.SUCCESS("Everything checkable is ready."))

    # ── Database ──────────────────────────────────────────────────────────────

    @staticmethod
    def database() -> Item:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            names = ", ".join(f"{m.app_label}.{m.name}" for m, _backwards in plan[:3])
            return Item(
                "Database",
                "Migrations",
                "blocking",
                f"{len(plan)} not applied ({names}{'…' if len(plan) > 3 else ''}) — "
                "run manage.py migrate; staffing checks skipped until then",
            )
        return Item("Database", "Migrations", "done", "all applied")

    # ── System checks ─────────────────────────────────────────────────────────

    @staticmethod
    def system_checks() -> list[Item]:
        """The project's own deploy checks: prices, tax copy, legal pages, secrets, …"""
        messages = run_checks(tags=["kuyash"], include_deployment_checks=True)
        if not messages:
            return [Item("System checks", "Project checks", "done", "all pass")]
        return [
            Item(
                "System checks",
                message.id or "check",
                "blocking" if message.is_serious() else "todo",
                f"{message.msg}" + (f" — {message.hint}" if message.hint else ""),
            )
            for message in messages
        ]

    # ── Operations ────────────────────────────────────────────────────────────

    @staticmethod
    def operations() -> list[Item]:
        items = []
        if getattr(settings, "SENTRY_DSN", ""):
            items.append(
                Item(
                    "Operations",
                    "Error reporting",
                    "done",
                    "SENTRY_DSN set — run manage.py sentry_check once to confirm scrubbing",
                )
            )
        else:
            items.append(
                Item(
                    "Operations", "Error reporting", "todo", "set SENTRY_DSN, then run sentry_check"
                )
            )

        if settings.ADMIN_ALLOWED_IPS:
            items.append(
                Item(
                    "Operations",
                    "Admin allowlist",
                    "done",
                    f"{len(settings.ADMIN_ALLOWED_IPS)} address range(s)",
                )
            )
        else:
            items.append(
                Item(
                    "Operations",
                    "Admin allowlist",
                    "todo",
                    "set ADMIN_ALLOWED_IPS, unless a VPN or network allowlist "
                    "already guards the admin",
                )
            )

        if settings.CELERY_TASK_ALWAYS_EAGER:
            items.append(
                Item(
                    "Operations",
                    "Scheduled work",
                    "todo",
                    "Celery runs eagerly here, so payment reconciliation and alerts never run",
                )
            )
        else:
            from apps.common.tasks import scheduler_status

            status = scheduler_status()
            items.append(
                Item(
                    "Operations",
                    "Scheduled work",
                    "done" if status == "ok" else "todo",
                    "beat is running"
                    if status == "ok"
                    else f"beat {status} — start the Celery beat process",
                )
            )
        return items

    # ── People ────────────────────────────────────────────────────────────────

    @staticmethod
    def people() -> list[Item]:
        from allauth.mfa.models import Authenticator

        from apps.accounts.models import User
        from apps.common.permissions import GROUP_KITCHEN, GROUP_MANAGERS
        from apps.delivery.models import DeliveryZone, RiderProfile

        items = []
        staff = User.objects.filter(is_active=True, is_staff=True)
        enrolled = set(
            Authenticator.objects.filter(type=Authenticator.Type.TOTP, user__in=staff).values_list(
                "user_id", flat=True
            )
        )
        missing = sorted(user.email for user in staff if user.pk not in enrolled)
        if not settings.STAFF_MFA_REQUIRED:
            items.append(Item("People", "Staff two-factor", "todo", "STAFF_MFA_REQUIRED is off"))
        elif not staff.exists():
            items.append(Item("People", "Staff two-factor", "todo", "no staff accounts exist yet"))
        elif missing:
            items.append(
                Item(
                    "People",
                    "Staff two-factor",
                    "todo",
                    f"{len(missing)} staff not yet enrolled (asked at their next admin sign-in): "
                    + ", ".join(missing[:5]),
                )
            )
        else:
            items.append(
                Item("People", "Staff two-factor", "done", f"all {staff.count()} staff enrolled")
            )

        for group, role, consequence in (
            (GROUP_KITCHEN, "Kitchen team", "nobody can use the kitchen display at /kitchen"),
            (
                GROUP_MANAGERS,
                "Managers",
                "nobody can refund, read reports or receive the stuck-orders email",
            ),
        ):
            count = User.objects.filter(is_active=True, groups__name=group).count()
            items.append(
                Item(
                    "People",
                    role,
                    "done" if count else "todo",
                    f"{count} in the {group} group"
                    if count
                    else f"{group} group is empty — {consequence}",
                )
            )

        if DeliveryZone.objects.filter(is_active=True).exists():
            riders = RiderProfile.objects.filter(user__is_active=True).count()
            items.append(
                Item(
                    "People",
                    "Riders",
                    "done" if riders else "todo",
                    f"{riders} rider profile(s)"
                    if riders
                    else "delivery zones are open but no rider profiles exist to assign",
                )
            )
        return items

    # ── By hand ───────────────────────────────────────────────────────────────

    @staticmethod
    def manual() -> list[Item]:
        return [
            Item("By hand", name, "manual", detail)
            for name, detail in (
                (
                    "Owner decisions",
                    "real prices, tax policy, rewards and About copy (DECISIONS.md)",
                ),
                (
                    "Content security policy",
                    "a real browser session on staging with no CSP errors (SECURITY.md §8)",
                ),
                (
                    "Backups",
                    "automated backups on and a restore drill recorded (DEPLOYMENT.md §8.2)",
                ),
                ("Secrets", "production secrets held in the platform's secret store"),
                ("Real payments", "the PRD §9 journey repeated on staging with Paystack test keys"),
                (
                    "Kitchen dry run",
                    "a practice service on /kitchen with the team (docs/KDS_GUIDE.md)",
                ),
            )
        ]
