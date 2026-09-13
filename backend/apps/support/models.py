"""Contact messages, tickets and the FAQ.

Replaces ``ContactForm.tsx:17``, which sets ``submitted = true``, shows a
success state, and resets after three seconds. The message never leaves the
component — it is not even placed in a variable that outlives the render.
"""

from __future__ import annotations

import secrets

from django.db import models

from apps.common.fields import PhoneField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.core.models import Branch

CHAT_TOKEN_BYTES = 32

TICKET_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_reference() -> str:
    for _ in range(12):
        candidate = "SUP-" + "".join(secrets.choice(TICKET_ALPHABET) for _ in range(6))
        if not Ticket.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Could not allocate a ticket reference.")  # pragma: no cover


class ContactReason(models.TextChoices):
    """Matches the buttons already on the contact form."""

    GENERAL = "general", "General"
    RESERVATION = "reservation", "Reservation"
    CATERING = "catering", "Catering"
    FEEDBACK = "feedback", "Feedback"
    PARTNERSHIP = "partnership", "Partnership"


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    PENDING = "pending", "Awaiting customer"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"


class ContactMessage(TimeStampedModel):
    """A raw submission from the contact form."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="contact_messages")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = PhoneField(blank=True)
    reason = models.CharField(
        max_length=20, choices=ContactReason.choices, default=ContactReason.GENERAL
    )
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)
    is_spam = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name}: {self.subject or self.reason}"


class Ticket(TimeStampedModel):
    """A conversation with a customer.

    Separate from the message so a phone call or a second email joins the same
    thread rather than starting a new one.
    """

    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="tickets")
    contact_message = models.OneToOneField(
        ContactMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name="ticket"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )

    requester_name = models.CharField(max_length=150)
    requester_email = models.EmailField()
    subject = models.CharField(max_length=200)
    reason = models.CharField(
        max_length=20, choices=ContactReason.choices, default=ContactReason.GENERAL
    )

    status = models.CharField(
        max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN, db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=TicketPriority.choices, default=TicketPriority.NORMAL
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.reference} — {self.subject}"

    @property
    def is_open(self) -> bool:
        return self.status in {TicketStatus.OPEN, TicketStatus.PENDING}


class TicketReply(TimeStampedModel):
    """One message in a ticket thread."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_replies",
        help_text="Blank for the customer.",
    )
    body = models.TextField()
    is_internal_note = models.BooleanField(
        default=False, help_text="Internal notes are never sent or shown to the customer."
    )
    sent_email = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        kind = "note" if self.is_internal_note else "reply"
        return f"{self.ticket.reference} {kind}"


class FaqEntry(TimeStampedModel, SoftDeleteModel):
    """A published answer.

    Serves the help page, and in Phase 3 the chat widget — which is why the
    bot will only ever be able to repeat what is written here.
    """

    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=80, blank=True)
    keywords = models.JSONField(
        default=list, blank=True, help_text="Extra terms that should match this answer."
    )
    display_order = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category", "display_order", "question"]
        verbose_name = "FAQ entry"
        verbose_name_plural = "FAQ entries"

    def __str__(self) -> str:
        return self.question


def generate_chat_token() -> str:
    return secrets.token_urlsafe(CHAT_TOKEN_BYTES)


class ChatSender(models.TextChoices):
    USER = "user", "Customer"
    BOT = "bot", "Assistant"


class ChatSession(TimeStampedModel):
    """One conversation with the chat assistant (ADR-012).

    Replaces a widget that matched a handful of hardcoded words to hardcoded
    replies — a US phone number, "dishes start from ₦6.90" — after a fake
    600 ms delay. The assistant can only repeat stored answers, look up an order
    the visitor can prove is theirs, or hand the conversation to a person.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="chat_sessions")
    session_token = models.CharField(
        max_length=64, unique=True, default=generate_chat_token, editable=False
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )
    #: What the assistant asked for last, so "KYS-7Q2M4P" after "What's your
    #: order reference?" is read as a reference.
    awaiting = models.CharField(max_length=30, blank=True)
    context = models.JSONField(default=dict, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    escalated_to_ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Chat {str(self.pk)[:8]}"


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=ChatSender.choices)
    body = models.TextField()
    matched_faq = models.ForeignKey(
        FaqEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_matches"
    )
    #: For assistant messages: suggested follow-ups, whether a handoff is
    #: offered, and a link (e.g. to an order page). Kept so a reopened
    #: conversation renders exactly as it did.
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.get_sender_display()}: {self.body[:40]}"
