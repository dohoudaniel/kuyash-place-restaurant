"""Notification dispatch.

Bodies come from editable :class:`EmailTemplate` rows, falling back to the
built-in wording in ``templates_data.py``. The fallback is deliberate: a
missing or malformed template must degrade the wording, never suppress an
order confirmation.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.notifications.models import Channel, Notification, NotificationStatus

logger = logging.getLogger(__name__)


class TemplateRenderError(Exception):
    """Raised only when even the built-in fallback cannot be rendered."""


def render_template(template_key: str, context: dict[str, Any]) -> tuple[str, str, str]:
    """Render a template to ``(subject, text_body, html_body)``.

    Resolution order: an active database row, then the built-in default. A row
    whose placeholders do not match the context falls back rather than raising —
    an admin typo must not stop a customer hearing that their order was taken.
    """
    from apps.notifications.models import EmailTemplate
    from apps.notifications.templates_data import DEFAULT_TEMPLATES

    default = DEFAULT_TEMPLATES.get(template_key)
    row = EmailTemplate.objects.filter(key=template_key, is_active=True).first()

    # Normalise both sources to the same shape before trying them, rather than
    # branching on type inside the loop.
    candidates: list[tuple[str, str, str, str]] = []
    if row is not None:
        candidates.append(("database", row.subject, row.text_body, row.html_body))
    if default is not None:
        candidates.append(
            ("builtin", default["subject"], default["text_body"], default.get("html_body", ""))
        )

    for origin, subject, text, html in candidates:
        try:
            return (
                subject.format(**context),
                text.format(**context),
                html.format(**context) if html else "",
            )
        except (KeyError, IndexError, ValueError):
            logger.warning(
                "email_template_render_failed",
                extra={"template": template_key, "origin": origin},
            )
            continue

    raise TemplateRenderError(f"No usable template for “{template_key}”.")


def queue_templated_email(
    *, template_key: str, recipient: str, context: dict[str, Any] | None = None
) -> Notification | None:
    """Render and queue an email. Returns ``None`` when there is no recipient."""
    if not recipient:
        return None
    context = context or {}
    try:
        subject, text, html = render_template(template_key, context)
    except TemplateRenderError:
        logger.exception("email_template_missing", extra={"template": template_key})
        return None
    return queue_email(
        template_key=template_key,
        recipient=recipient,
        subject=subject,
        body=text,
        html_body=html,
        context=context,
    )


def queue_email(
    *,
    template_key: str,
    recipient: str,
    subject: str,
    body: str,
    html_body: str = "",
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
        html_body=html_body,
        context=context or {},
    )
    dispatch(notification)
    # The worker loads its own copy, so ours is stale the moment the task runs.
    # Refresh so callers see the real outcome rather than a stale "queued" —
    # though inside a transaction the send is deliberately deferred to COMMIT,
    # so "queued" is the honest answer until then.
    notification.refresh_from_db()
    return notification


def dispatch(notification: Notification) -> None:
    """Hand a recorded notification to the worker, once the row is committed.

    ``register_user`` and ``place_order`` are ``@transaction.atomic``, and a
    task published inside an open transaction is visible to workers *before*
    ``COMMIT``. A worker that picked it up first found no such row, returned
    ``"missing"`` and exited — no exception, no retry, no log. The customer was
    told to check their email and never received it, and because verification is
    mandatory they could then never sign in.

    ``transaction.on_commit`` is the pattern ``apps/realtime`` already uses for
    the same reason. Outside a transaction it runs the callback immediately, so
    callers that are not in one are unaffected.
    """
    from apps.notifications.tasks import deliver_notification

    notification_id = str(notification.pk)

    def publish() -> None:
        deliver_notification.delay(notification_id)

    transaction.on_commit(publish)


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
        message = EmailMultiAlternatives(
            subject=notification.subject,
            body=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification.recipient],
        )
        if notification.html_body:
            message.attach_alternative(notification.html_body, "text/html")
        message.send(fail_silently=False)
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
