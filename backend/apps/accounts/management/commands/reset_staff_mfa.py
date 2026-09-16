"""Break-glass: clear a staff member's two-factor authenticators.

The admin action that does the same thing is superuser-only and lives *behind*
the two-factor gate, so a sole superuser who loses their phone locks themselves
out of the entire admin — including the page that would let them fix it — in the
middle of service. This is the way back in, and it needs only shell access.

Deliberately not a "disable MFA" switch: it clears the enrolment so the person
re-enrols (new secret, new recovery codes) at their next admin sign-in.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.accounts.models import User
from apps.accounts.staff_mfa import reset_for

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clear a staff member's two-factor authenticators so they can re-enrol."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email", help="The staff member's email address.")

    def handle(self, *args: Any, **options: Any) -> None:
        email = str(options["email"]).lower().strip()
        user = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"No account with the email “{email}”.")

        deleted = reset_for(user)
        # Someone bypassing the admin's own controls is worth a line in the log
        # whether or not it found anything to remove.
        logger.warning("staff_mfa_reset_from_cli", extra={"user": str(user.pk)})

        if not deleted:
            self.stdout.write(f"{email} had no authenticators enrolled — nothing to reset.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared two-factor authentication for {email}. "
                "They will be asked to enrol again at their next admin sign-in."
            )
        )
