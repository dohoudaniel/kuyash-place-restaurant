"""Notification outbox.

Every send is recorded (NOT-3). When a customer says "I never got my
confirmation", this table is what answers the question.

Delivery is published with ``transaction.on_commit``, so these tests execute the
pending callbacks explicitly rather than assuming the send already happened —
which is the whole point: in production it had not.
"""

from __future__ import annotations

from unittest import mock

import pytest
from django.core import mail

from apps.notifications import tasks
from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.services import deliver, queue_email

pytestmark = pytest.mark.django_db


def queue(**overrides):  # type: ignore[no-untyped-def]
    return queue_email(
        **{
            "template_key": "verify_email",
            "recipient": "ada@example.com",
            "subject": "Confirm your email",
            "body": "Follow the link.",
            **overrides,
        }
    )


# ── Recording and sending ─────────────────────────────────────────────────────


def test_queueing_records_and_sends(mailoutbox, django_capture_on_commit_callbacks) -> None:  # type: ignore[no-untyped-def]
    with django_capture_on_commit_callbacks(execute=True):
        notification = queue()

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert notification.attempts == 1
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["ada@example.com"]


def test_the_email_is_not_published_until_the_transaction_commits(  # type: ignore[no-untyped-def]
    django_capture_on_commit_callbacks,
) -> None:
    """**The regression test for the P0.**

    ``register_user`` is ``@transaction.atomic`` and used to call
    ``deliver_notification.delay()`` directly inside it. In production the task
    reached Redis before ``COMMIT``, so a worker could pick it up, find no such
    row, return ``"missing"`` and exit — no exception, no retry, no log. The
    customer was told to check their email, never got it, and because
    verification is mandatory could then never sign in.

    The row must exist before the task is published, and nothing may be
    published while the transaction is still open.
    """
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        notification = queue()
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.QUEUED
        assert notification.attempts == 0
        assert not mail.outbox

    assert len(callbacks) == 1, "exactly one delivery should be scheduled, on commit"

    callbacks[0]()
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert Notification.objects.get(pk=notification.pk).sent_at is not None


class _Rollback(Exception):
    """Aborts the inner transaction in the test below."""


def test_a_rolled_back_transaction_sends_nothing(  # type: ignore[no-untyped-def]
    django_capture_on_commit_callbacks,
) -> None:
    """The mirror image: an email for a row that never existed must not go out.

    Publishing before ``COMMIT`` got this wrong in both directions — it could
    send for a row that was about to disappear, as well as lose one that stayed.
    """
    from django.db import transaction

    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(_Rollback), transaction.atomic():
            queue()
            raise _Rollback

    assert not mail.outbox
    assert not Notification.objects.exists()


# ── Failure, and recovery from it ─────────────────────────────────────────────


def test_a_failed_send_is_recorded_not_swallowed(django_capture_on_commit_callbacks) -> None:  # type: ignore[no-untyped-def]
    """A message we failed to send is a different problem from one we never
    attempted, and the difference matters when a customer is on the phone."""
    with mock.patch(
        "apps.notifications.services.EmailMultiAlternatives.send",
        side_effect=OSError("SMTP unreachable"),
    ):
        with django_capture_on_commit_callbacks(execute=True):
            notification = queue()

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED
    assert "OSError" in notification.error
    assert notification.attempts == 1
    assert notification.sent_at is None


def test_a_failed_send_can_be_retried(django_capture_on_commit_callbacks) -> None:  # type: ignore[no-untyped-def]
    with mock.patch(
        "apps.notifications.services.EmailMultiAlternatives.send",
        side_effect=OSError("down"),
    ):
        with django_capture_on_commit_callbacks(execute=True):
            notification = queue()
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED

    deliver(notification)
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 2


def test_delivering_an_already_sent_notification_is_a_no_op(  # type: ignore[no-untyped-def]
    mailoutbox, django_capture_on_commit_callbacks
) -> None:
    """Guards against a duplicate email if a task is retried after success."""
    with django_capture_on_commit_callbacks(execute=True):
        notification = queue()
    assert len(mail.outbox) == 1

    deliver(notification)
    assert len(mail.outbox) == 1
    assert notification.attempts == 1


# ── The task itself ───────────────────────────────────────────────────────────


def test_missing_notification_does_not_crash_the_task() -> None:
    import uuid

    assert tasks.deliver_notification(str(uuid.uuid4())) == "missing"


def test_a_failed_delivery_asks_celery_to_retry(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``deliver()`` returns normally after recording FAILED, so without an
    explicit ``retry()`` Celery saw a *successful* task and the email was lost.

    The task declared ``max_retries=3`` for a long time while nothing ever
    called ``retry()`` — the declaration was pure decoration.
    """
    from celery.exceptions import Retry

    asked: dict[str, object] = {}

    def fake_retry(*, exc=None, countdown=None, **kwargs):  # type: ignore[no-untyped-def]
        asked["countdown"] = countdown
        asked["exc"] = exc
        raise Retry()

    monkeypatch.setattr(tasks.deliver_notification, "retry", fake_retry)

    notification = Notification.objects.create(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
    )
    with mock.patch(
        "apps.notifications.services.EmailMultiAlternatives.send",
        side_effect=OSError("SMTP unreachable"),
    ):
        with pytest.raises(Retry):
            tasks.deliver_notification(str(notification.pk))

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED
    assert isinstance(asked["exc"], tasks.NotificationDeliveryFailed)
    assert isinstance(asked["countdown"], int)
    assert asked["countdown"] >= tasks.RETRY_BASE_SECONDS // 2


def test_a_successful_delivery_does_not_retry(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def explode(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a successful send must not be retried")

    monkeypatch.setattr(tasks.deliver_notification, "retry", explode)
    notification = Notification.objects.create(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
    )
    assert tasks.deliver_notification(str(notification.pk)) == NotificationStatus.SENT


def test_the_backoff_grows_and_respects_its_ceiling() -> None:
    for retries in range(6):
        ceiling = min(tasks.RETRY_BASE_SECONDS * 2**retries, tasks.RETRY_MAX_SECONDS)
        assert ceiling / 2 <= tasks.retry_delay(retries) <= ceiling
    assert tasks.retry_delay(20) <= tasks.RETRY_MAX_SECONDS


def test_the_backoff_is_jittered() -> None:
    """An SMTP outage fails every queued email at once; without jitter they all
    retry in the same second and fail together again."""
    assert len({tasks.retry_delay(5) for _ in range(40)}) > 1


def test_the_task_acknowledges_late() -> None:
    """Without this a worker that dies mid-send loses the task, and the
    customer's confirmation with it."""
    assert tasks.deliver_notification.acks_late is True
    assert tasks.deliver_notification.max_retries == tasks.MAX_RETRIES


# ── Ordering ──────────────────────────────────────────────────────────────────


def test_notifications_are_ordered_newest_first() -> None:
    first = Notification.objects.create(template_key="a", recipient="x@example.com")
    second = Notification.objects.create(template_key="b", recipient="y@example.com")
    assert list(Notification.objects.all()) == [second, first]
