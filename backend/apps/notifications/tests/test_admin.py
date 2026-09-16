"""The notification admin.

It is a log, so it is read-only — but it needed one way to act: a verification
email that failed to send leaves a customer who can never sign in, and until now
there was no requeue action, no sweep task and no CLI path to recover it.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus

pytestmark = pytest.mark.django_db

CHANGELIST = reverse("admin:notifications_notification_changelist")


@pytest.fixture
def failed_notification() -> Notification:
    return Notification.objects.create(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
        status=NotificationStatus.FAILED,
        error="OSError: SMTP unreachable",
        attempts=1,
    )


@pytest.fixture
def root(db) -> User:  # type: ignore[no-untyped-def]
    return User.objects.create_superuser(email="root@example.com", password="x" * 16)


def requeue(client, notification: Notification):  # type: ignore[no-untyped-def]
    return client.post(
        CHANGELIST,
        {"action": "requeue", "_selected_action": [str(notification.pk)]},
        follow=True,
    )


def test_a_failed_notification_can_be_requeued(  # type: ignore[no-untyped-def]
    client, root, failed_notification, mailoutbox, django_capture_on_commit_callbacks
) -> None:
    client.force_login(root)

    with django_capture_on_commit_callbacks(execute=True):
        response = requeue(client, failed_notification)

    assert "Requeued 1 notification" in response.content.decode()
    failed_notification.refresh_from_db()
    assert failed_notification.status == NotificationStatus.SENT
    assert failed_notification.error == ""
    assert failed_notification.attempts == 2
    assert [message.to for message in mailoutbox] == [["ada@example.com"]]


def test_a_stuck_queued_notification_can_be_requeued(  # type: ignore[no-untyped-def]
    client, root, mailoutbox, django_capture_on_commit_callbacks
) -> None:
    """The row left behind when a task was published before its transaction
    committed: queued forever, with nothing to retry it."""
    stuck = Notification.objects.create(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
    )
    client.force_login(root)

    with django_capture_on_commit_callbacks(execute=True):
        requeue(client, stuck)

    stuck.refresh_from_db()
    assert stuck.status == NotificationStatus.SENT
    assert len(mailoutbox) == 1


def test_an_already_sent_notification_is_not_resent(  # type: ignore[no-untyped-def]
    client, root, mailoutbox, django_capture_on_commit_callbacks
) -> None:
    """Resending a delivered message would put a duplicate in the inbox."""
    sent = Notification.objects.create(
        template_key="verify_email",
        recipient="ada@example.com",
        subject="Confirm your email",
        body="Follow the link.",
        status=NotificationStatus.SENT,
    )
    client.force_login(root)

    with django_capture_on_commit_callbacks(execute=True):
        response = requeue(client, sent)

    assert "Skipped 1 already sent" in response.content.decode()
    sent.refresh_from_db()
    assert sent.status == NotificationStatus.SENT
    assert not mailoutbox


def test_requeueing_needs_change_permission(  # type: ignore[no-untyped-def]
    client, failed_notification, mailoutbox, django_capture_on_commit_callbacks
) -> None:
    viewer = User.objects.create_user(email="viewer@example.com", password="x" * 16, is_staff=True)
    viewer.user_permissions.add(Permission.objects.get(codename="view_notification"))
    client.force_login(viewer)

    with django_capture_on_commit_callbacks(execute=True):
        response = requeue(client, failed_notification)

    assert "need change permission" in response.content.decode()
    failed_notification.refresh_from_db()
    assert failed_notification.status == NotificationStatus.FAILED
    assert not mailoutbox


def test_the_notification_page_stays_read_only(client, root, failed_notification) -> None:  # type: ignore[no-untyped-def]
    """Requeueing is a recovery action, not a licence to edit the log."""
    client.force_login(root)
    assert client.get(CHANGELIST).status_code == 200

    change_url = reverse("admin:notifications_notification_change", args=[failed_notification.pk])
    page = client.get(change_url, follow=True)
    assert page.status_code == 200
    assert b'name="_save"' not in page.content
