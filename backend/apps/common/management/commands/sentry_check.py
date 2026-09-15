"""Send one test event to Sentry and say where to look (SECURITY.md §8).

Ticking "Sentry live with PII scrubbing confirmed" needs a real event to
inspect. This sends a message event carrying fields that must be scrubbed, so
the event in Sentry shows ``[redacted]`` where the secrets were.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test event to Sentry, with fields that must arrive redacted."

    def handle(self, *args: Any, **options: Any) -> None:
        if not sentry_sdk.get_client().is_active():
            raise CommandError(
                "Sentry is not initialised. Set SENTRY_DSN and run with production settings."
            )
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("kuyash.check", "sentry_check")
            scope.set_context(
                "scrubbing_probe",
                {"password": "must-not-arrive", "card_number": "4242424242424242", "ok": "visible"},
            )
            event_id = sentry_sdk.capture_message("Kuyash Sentry check", level="info")
        sentry_sdk.flush(timeout=10)
        if not event_id:
            raise CommandError("Sentry dropped the event (sampling or before_send).")
        self.stdout.write(self.style.SUCCESS(f"Sent event {event_id}."))
        self.stdout.write(
            "In Sentry, open it and confirm the scrubbing_probe context shows "
            "password and card_number as [redacted] and ok as visible."
        )
