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
    body = models.TextField(blank=True)
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
