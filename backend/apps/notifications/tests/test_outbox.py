"""Notification outbox.

Every send is recorded (NOT-3). When a customer says "I never got my
confirmation", this table is what answers the question.
"""

from __future__ import annotations

from unittest import mock

import pytest
from django.core import mail

from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.services import deliver, queue_email

pytestmark = pytest.mark.django_db


def test_queueing_records_and_sends(mailoutbox) -> None:  # type: ignore[no-untyped-def]
    notification = queue_email(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
    )
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert notification.attempts == 1
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["ada@example.com"]


def test_a_failed_send_is_recorded_not_swallowed() -> None:
    """A message we failed to send is a different problem from one we never
    attempted, and the difference matters when a customer is on the phone."""
    with mock.patch(
        "apps.notifications.services.EmailMultiAlternatives.send",
        side_effect=OSError("SMTP unreachable"),
    ):
        notification = queue_email(
            template_key="verify_email",
            recipient="ada@example.com",
            subject="Confirm your email",
            body="Follow the link.",
        )

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED
    assert "OSError" in notification.error
    assert notification.attempts == 1
    assert notification.sent_at is None


def test_a_failed_send_can_be_retried() -> None:
    with mock.patch(
        "apps.notifications.services.EmailMultiAlternatives.send",
        side_effect=OSError("down"),
    ):
        notification = queue_email(
            template_key="verify_email",
            recipient="ada@example.com",
            subject="Subject",
            body="Body",
        )
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED

    deliver(notification)
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 2


def test_delivering_an_already_sent_notification_is_a_no_op(mailoutbox) -> None:  # type: ignore[no-untyped-def]
    """Guards against a duplicate email if a task is retried after success."""
    notification = queue_email(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Subject",
        body="Body",
    )
    assert len(mail.outbox) == 1

    deliver(notification)
    assert len(mail.outbox) == 1
    assert notification.attempts == 1


def test_missing_notification_does_not_crash_the_task() -> None:
    import uuid

    from apps.notifications.tasks import deliver_notification

    assert deliver_notification(str(uuid.uuid4())) == "missing"


def test_notifications_are_ordered_newest_first() -> None:
    first = Notification.objects.create(template_key="a", recipient="x@example.com")
    second = Notification.objects.create(template_key="b", recipient="y@example.com")
    assert list(Notification.objects.all()) == [second, first]
