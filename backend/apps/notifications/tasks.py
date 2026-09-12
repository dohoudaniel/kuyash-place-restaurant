"""Celery tasks for notifications."""

from __future__ import annotations

from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.services import deliver


@shared_task(name="notifications.deliver", bind=True, max_retries=3)
def deliver_notification(self, notification_id: str) -> str:  # type: ignore[no-untyped-def]
    """Deliver one queued notification.

    Runs eagerly in local development (no Redis required — see ADR-015).
    """
    try:
        notification = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:  # pragma: no cover - defensive
        return "missing"
    return deliver(notification).status
