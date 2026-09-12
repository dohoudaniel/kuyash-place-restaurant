"""Support services."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import DomainError
from apps.support.models import (
    ContactMessage,
    ContactReason,
    Ticket,
    TicketReply,
    TicketStatus,
)

logger = logging.getLogger(__name__)

#: Crude but effective: a human filling in a contact form does not paste six URLs.
MAX_LINKS = 4
SPAM_PHRASES = ("viagra", "casino", "crypto giveaway", "seo services", "backlinks")


class MessageRejected(DomainError):
    code = "message_rejected"
    title = "That message could not be sent"
    status_code = 422


def looks_like_spam(*, message: str, subject: str = "", honeypot: str = "") -> bool:
    """Cheap heuristics, applied before anything reaches a human.

    Deliberately not clever. The cost of a false negative is one junk ticket;
    the cost of a false positive is a lost customer, so the thresholds are
    generous.
    """
    if honeypot.strip():
        # A field hidden from humans was filled in. Only a bot does that.
        return True

    body = f"{subject}\n{message}".lower()
    if body.count("http://") + body.count("https://") > MAX_LINKS:
        return True
    return any(phrase in body for phrase in SPAM_PHRASES)


@transaction.atomic
def submit_contact_message(
    *,
    branch: Any,
    name: str,
    email: str,
    message: str,
    reason: str = ContactReason.GENERAL,
    subject: str = "",
    phone: str = "",
    user: Any = None,
    honeypot: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
) -> Ticket | None:
    """Record a contact message and open a ticket.

    Returns ``None`` for spam — recorded and quarantined, never raised, so a bot
    learns nothing from the response.
    """
    if not message.strip():
        raise MessageRejected("Please tell us how we can help.")

    spam = looks_like_spam(message=message, subject=subject, honeypot=honeypot)

    contact = ContactMessage.objects.create(
        branch=branch,
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        reason=reason,
        subject=subject.strip(),
        message=message.strip(),
        ip_address=ip_address,
        user_agent=user_agent[:400],
        is_spam=spam,
    )
    if spam:
        logger.info("contact_message_quarantined", extra={"message": str(contact.pk)})
        return None

    ticket = Ticket.objects.create(
        branch=branch,
        contact_message=contact,
        user=user if user is not None and getattr(user, "is_authenticated", False) else None,
        requester_name=contact.name,
        requester_email=contact.email,
        subject=contact.subject or f"{contact.get_reason_display()} enquiry",
        reason=contact.reason,
    )
    TicketReply.objects.create(ticket=ticket, body=contact.message)

    _acknowledge(ticket)
    _alert_team(ticket)
    return ticket


def _acknowledge(ticket: Ticket) -> None:
    from apps.notifications.services import queue_templated_email

    queue_templated_email(
        template_key="contact_received",
        recipient=ticket.requester_email,
        context={
            "name": ticket.requester_name.split(" ")[0] or "there",
            "reference": ticket.reference,
            "subject": ticket.subject,
        },
    )


def _alert_team(ticket: Ticket) -> None:
    from apps.core.models import SiteSettings
    from apps.notifications.services import queue_templated_email

    settings_row = SiteSettings.load()
    recipient = settings_row.support_email or settings_row.orders_email
    if not recipient:
        return
    queue_templated_email(
        template_key="contact_internal",
        recipient=recipient,
        context={
            "reference": ticket.reference,
            "name": ticket.requester_name,
            "email": ticket.requester_email,
            "reason": ticket.get_reason_display(),
            "subject": ticket.subject,
            "message": first_reply.body if (first_reply := ticket.replies.first()) else "",
        },
    )


@transaction.atomic
def reply_to_ticket(
    *, ticket: Ticket, body: str, author: Any = None, internal: bool = False
) -> TicketReply:
    """Add a reply, and email the customer unless it is an internal note."""
    if not body.strip():
        raise MessageRejected("A reply cannot be empty.")

    reply = TicketReply.objects.create(
        ticket=ticket,
        author=author if author is not None and getattr(author, "pk", None) else None,
        body=body.strip(),
        is_internal_note=internal,
    )

    if not internal:
        from apps.notifications.services import queue_templated_email

        queue_templated_email(
            template_key="ticket_reply",
            recipient=ticket.requester_email,
            context={
                "name": ticket.requester_name.split(" ")[0] or "there",
                "reference": ticket.reference,
                "subject": ticket.subject,
                "body": reply.body,
            },
        )
        reply.sent_email = True
        reply.save(update_fields=["sent_email", "updated_at"])

        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.PENDING
            ticket.save(update_fields=["status", "updated_at"])

    return reply


def resolve_ticket(*, ticket: Ticket, actor: Any = None) -> Ticket:
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = timezone.now()
    if actor is not None and getattr(actor, "pk", None) and ticket.assigned_to is None:
        ticket.assigned_to = actor
    ticket.save()
    return ticket
