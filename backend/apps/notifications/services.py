"""Notification dispatch.

Phase 1F replaces the inline bodies here with editable ``EmailTemplate`` rows.
The outbox record and the send path are already in their final shape.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone

from apps.notifications.models import Channel, Notification, NotificationStatus

logger = logging.getLogger(__name__)


def queue_email(
    *,
    template_key: str,
    recipient: str,
    subject: str,
    body: str,
    context: dict[str, Any] | None = None,
) -> Notification:
    """Record an email and hand it to the worker.

    Recording happens first and unconditionally: a message we failed to send is
    a different problem from a message we never attempted, and the difference
    matters when a customer is on the phone.
    """
    notification = Notification.objects.create(
        channel=Channel.EMAIL,
        template_key=template_key,
        recipient=recipient,
        subject=subject,
        body=body,
        context=context or {},
    )
    from apps.notifications.tasks import deliver_notification

    deliver_notification.delay(str(notification.pk))
    # The worker loads its own copy, so ours is stale the moment the task runs
    # (which is immediately when Celery is eager). Refresh so callers see the
    # real outcome rather than a permanent "queued".
    notification.refresh_from_db()
    return notification


def deliver(notification: Notification) -> Notification:
    """Send one recorded notification. Idempotent on already-sent records.

    The guard is a conditional UPDATE rather than a check on the in-memory
    object: once a worker has sent the message, any caller still holding the
    pre-send instance would otherwise see ``queued`` and send it a second time.
    A conditional UPDATE is atomic on both SQLite and Postgres, so this needs no
    row locking (``select_for_update`` is unavailable on SQLite — ADR-015).
    """
    claimed = (
        Notification.objects.filter(pk=notification.pk)
        .exclude(status=NotificationStatus.SENT)
        .update(attempts=F("attempts") + 1, updated_at=timezone.now())
    )
    notification.refresh_from_db()
    if not claimed:
        return notification

    try:
        send_mail(
            subject=notification.subject,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient],
            fail_silently=False,
        )
    except Exception as exc:
        notification.status = NotificationStatus.FAILED
        notification.error = f"{exc.__class__.__name__}: {exc}"
        notification.save(update_fields=["status", "error", "updated_at"])
        logger.exception("notification_send_failed", extra={"notification": str(notification.pk)})
        return notification

    notification.status = NotificationStatus.SENT
    notification.sent_at = timezone.now()
    notification.error = ""
    notification.save(update_fields=["status", "sent_at", "error", "updated_at"])
    return notification
