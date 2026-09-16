"""Celery tasks for notifications."""

from __future__ import annotations

import logging
import random

from celery import shared_task

from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.services import deliver

logger = logging.getLogger(__name__)

#: First retry after roughly a minute, then doubling to a half-hour ceiling.
RETRY_BASE_SECONDS = 60
RETRY_MAX_SECONDS = 30 * 60
MAX_RETRIES = 5


class NotificationDeliveryFailed(Exception):
    """Carries the send error into Celery's retry machinery and its logs."""


def retry_delay(retries: int) -> int:
    """Exponential backoff with jitter.

    The jitter matters more than the backoff: an SMTP outage fails every queued
    email at once, and without it all of them would retry in the same second and
    fail together again, repeatedly.
    """
    ceiling = min(RETRY_BASE_SECONDS * (2**retries), RETRY_MAX_SECONDS)
    return int(random.uniform(ceiling / 2, ceiling))  # noqa: S311 - jitter, not crypto


@shared_task(
    name="notifications.deliver",
    bind=True,
    max_retries=MAX_RETRIES,
    # Without acks_late a worker that dies mid-send loses the task silently, and
    # the customer's confirmation with it.
    acks_late=True,
)
def deliver_notification(self, notification_id: str) -> str:  # type: ignore[no-untyped-def]
    """Deliver one queued notification, retrying a failed send.

    ``deliver()`` catches the send error, records FAILED and returns normally —
    so without an explicit ``retry()`` here the task exits *successfully* and
    Celery believes the email went out. ``max_retries`` was declared on this
    task for a long time while nothing ever called ``retry()``, which meant one
    SMTP blip permanently lost a verification email.

    Runs eagerly in local development (no Redis required — see ADR-015).
    """
    try:
        notification = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        # No longer expected: the task is published on commit, so the row is
        # always there by the time a worker reads it. Still logged rather than
        # swallowed, because silence here is what hid the original bug.
        logger.warning("notification_missing", extra={"notification": notification_id})
        return "missing"

    notification = deliver(notification)
    if notification.status != NotificationStatus.FAILED:
        return str(notification.status)

    if self.request.is_eager:
        # Eager mode has no broker, so a retry would re-run the send inline in
        # the caller's own request. Dev and tests stop at FAILED; the admin's
        # "requeue" action is the recovery path there.
        return str(notification.status)

    logger.warning(
        "notification_delivery_retrying",
        extra={"notification": notification_id, "attempt": self.request.retries + 1},
    )
    raise self.retry(
        exc=NotificationDeliveryFailed(notification.error or "delivery failed"),
        countdown=retry_delay(self.request.retries),
    )
