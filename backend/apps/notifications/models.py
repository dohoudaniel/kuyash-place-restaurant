"""Outbound notification records."""

from __future__ import annotations

from django.db import models

from apps.common.models import TimeStampedModel


class Channel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"  # reserved — see ADR-011
    WHATSAPP = "whatsapp", "WhatsApp"  # reserved


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Notification(TimeStampedModel):
    """One outbound message.

    Every send is recorded (NOT-3). When a customer says "I never got my
    confirmation", this table answers the question instead of a shrug.
    """

    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    template_key = models.CharField(
        max_length=80, db_index=True, help_text="e.g. verify_email, password_reset"
    )
    recipient = models.CharField(max_length=254, db_index=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True, help_text="Plain-text body as sent.")
    html_body = models.TextField(blank=True, help_text="HTML alternative, if any.")
    context = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.QUEUED,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["template_key", "status"])]

    def __str__(self) -> str:
        return f"{self.template_key} → {self.recipient} ({self.status})"


class EmailTemplate(TimeStampedModel):
    """An editable email body.

    Staff change wording without a deploy. Every template has a built-in
    fallback in ``apps/notifications/templates_data.py``, so a missing or
    deleted row can never stop an order confirmation from going out — the
    message degrades to the default rather than disappearing.
    """

    key = models.CharField(
        max_length=80,
        unique=True,
        help_text="Identifier used in code, e.g. order_confirmation. Do not change.",
    )
    description = models.CharField(max_length=255, blank=True, help_text="When this email is sent.")
    subject = models.CharField(max_length=255)
    text_body = models.TextField(help_text="Plain-text version. Always sent.")
    html_body = models.TextField(
        blank=True, help_text="Optional HTML version, sent as an alternative part."
    )
    available_context = models.JSONField(
        default=list,
        blank=True,
        help_text="Placeholder names available to this template, for reference.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Turning this off falls back to the built-in wording, not to silence.",
    )

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key
