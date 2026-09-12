"""Catering services."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catering.models import (
    RESPONSE_SLA,
    CateringEnquiry,
    CateringPackage,
    EnquiryStatus,
)
from apps.common.exceptions import DomainError

logger = logging.getLogger(__name__)


class EnquiryRejected(DomainError):
    code = "enquiry_rejected"
    title = "That enquiry cannot be submitted"
    status_code = 422


@transaction.atomic
def submit_enquiry(
    *,
    branch: Any,
    name: str,
    email: str,
    phone: str,
    guest_count: int,
    package: CateringPackage | None = None,
    event_type: str = "",
    event_date: Any = None,
    event_time: Any = None,
    venue: str = "",
    message: str = "",
    user: Any = None,
    ip_address: str | None = None,
) -> CateringEnquiry:
    """Record an enquiry, acknowledge the customer, and alert the team.

    All three matter. The current form does none of them.
    """
    if guest_count < 1:
        raise EnquiryRejected("Tell us roughly how many guests you expect.")

    if package is not None and not package.suits(guest_count):
        raise EnquiryRejected(
            f"{package.name} covers {package.min_guests}–{package.max_guests} guests. "
            "Choose another package, or leave it blank and we will advise."
        )

    if event_date is not None and event_date < timezone.localdate():
        raise EnquiryRejected("That date has already passed.")

    enquiry = CateringEnquiry.objects.create(
        branch=branch,
        user=user if user is not None and getattr(user, "is_authenticated", False) else None,
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        guest_count=guest_count,
        package=package,
        indicative_total=package.indicative_total(guest_count) if package else 0,
        event_type=event_type.strip(),
        event_date=event_date,
        event_time=event_time,
        venue=venue.strip(),
        message=message.strip(),
        ip_address=ip_address,
    )

    _acknowledge(enquiry)
    _alert_team(enquiry)

    logger.info(
        "catering_enquiry_received",
        extra={"reference": enquiry.reference, "guests": guest_count},
    )
    return enquiry


def _acknowledge(enquiry: CateringEnquiry) -> None:
    """Tell the customer we have it, and by when they will hear back."""
    from apps.carts.serializers import money
    from apps.notifications.services import queue_templated_email

    indicative = (
        f"Indicative total: {money(enquiry.indicative_total, enquiry.branch.currency)['display']} "
        f"({enquiry.guest_count} guests × {enquiry.package.name})"
        if enquiry.package and enquiry.indicative_total
        else "We will price this for you once we know a little more."
    )
    queue_templated_email(
        template_key="catering_enquiry_received",
        recipient=enquiry.email,
        context={
            "name": enquiry.name.split(" ")[0] or "there",
            "reference": enquiry.reference,
            "guest_count": enquiry.guest_count,
            "indicative_line": indicative,
            "respond_by": timezone.localtime(enquiry.respond_by, enquiry.branch.tzinfo()).strftime(
                "%A %d %B at %H:%M"
            ),
        },
    )


def _alert_team(enquiry: CateringEnquiry) -> None:
    """Put the enquiry in front of a human.

    Without this the record exists but nobody is prompted — which is only
    marginally better than the current console.log.
    """
    from apps.core.models import SiteSettings
    from apps.notifications.services import queue_templated_email

    recipient = SiteSettings.load().orders_email or settings.DEFAULT_FROM_EMAIL
    if "<" in recipient:  # "Name <addr>" form
        recipient = recipient.split("<")[-1].rstrip(">")

    queue_templated_email(
        template_key="catering_enquiry_internal",
        recipient=recipient,
        context={
            "reference": enquiry.reference,
            "name": enquiry.name,
            "email": enquiry.email,
            "phone": enquiry.phone,
            "guest_count": enquiry.guest_count,
            "event_type": enquiry.event_type or "not specified",
            "event_date": enquiry.event_date.isoformat() if enquiry.event_date else "not specified",
            "venue": enquiry.venue or "not specified",
            "message": enquiry.message or "(none)",
            "respond_by": timezone.localtime(enquiry.respond_by, enquiry.branch.tzinfo()).strftime(
                "%A %d %B at %H:%M"
            ),
        },
    )


@transaction.atomic
def record_response(
    *,
    enquiry: CateringEnquiry,
    status: str = EnquiryStatus.CONTACTED,
    quoted_amount: int | None = None,
    notes: str = "",
    actor: Any = None,
) -> CateringEnquiry:
    """Mark an enquiry as answered. Stops the SLA clock."""
    enquiry.status = status
    if quoted_amount is not None:
        enquiry.quoted_amount = quoted_amount
    if notes:
        separator = "\n\n" if enquiry.internal_notes else ""
        enquiry.internal_notes = f"{enquiry.internal_notes}{separator}{notes}"
    if enquiry.responded_at is None:
        enquiry.responded_at = timezone.now()
    if actor is not None and getattr(actor, "pk", None) and enquiry.assigned_to is None:
        enquiry.assigned_to = actor
    enquiry.save()
    return enquiry


def overdue_enquiries(branch: Any) -> list[CateringEnquiry]:
    """Enquiries past the 24 hours the website promises.

    The list a manager should be looking at every morning.
    """
    cutoff = timezone.now() - RESPONSE_SLA
    return list(
        CateringEnquiry.objects.filter(
            branch=branch,
            status=EnquiryStatus.NEW,
            responded_at__isnull=True,
            created_at__lt=cutoff,
        ).order_by("created_at")
    )
