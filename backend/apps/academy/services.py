"""Enrolment rules: seats, holds, payment, completion and certificates."""

from __future__ import annotations

import datetime as dt
import io
import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import Http404
from django.utils import timezone
from rest_framework import status

from apps.academy.models import (
    SEATED_STATUSES,
    Cohort,
    CohortStatus,
    Enrolment,
    EnrolmentPaymentMethod,
    EnrolmentStatus,
)
from apps.common.exceptions import DomainError, PriceChanged
from apps.common.money import format_money

logger = logging.getLogger(__name__)


class AcademyConflict(DomainError):
    status_code = status.HTTP_409_CONFLICT


class CohortUnavailable(AcademyConflict):
    code = "cohort_unavailable"
    title = "This class is not open for enrolment"


class CohortFull(AcademyConflict):
    code = "cohort_full"
    title = "This class is full"


class AlreadyEnrolled(AcademyConflict):
    code = "already_enrolled"
    title = "You are already enrolled in this class"


class TransferUnavailable(AcademyConflict):
    code = "transfer_unavailable"
    title = "Bank transfer is not available"


class EnrolmentNotPayable(AcademyConflict):
    code = "enrolment_not_payable"
    title = "This enrolment cannot be paid online"


class EnrolmentExpired(AcademyConflict):
    code = "enrolment_expired"
    title = "Your seat hold has expired"


class EnrolmentStateError(AcademyConflict):
    code = "enrolment_state"
    title = "That can't be done to this enrolment"


class CertificateNotAvailable(AcademyConflict):
    code = "certificate_not_available"
    title = "No certificate has been issued yet"


# ──────────────────────────────────────────────────────────────────────────────
# Seats
# ──────────────────────────────────────────────────────────────────────────────


def holding_seats(cohort: Cohort, *, now: dt.datetime | None = None) -> QuerySet[Enrolment]:
    """Enrolments that occupy a seat: paid ones, and unpaid ones still on hold."""
    now = now or timezone.now()
    return Enrolment.objects.filter(cohort=cohort).filter(
        Q(status__in=SEATED_STATUSES)
        | Q(status=EnrolmentStatus.PENDING_PAYMENT, hold_expires_at__gt=now)
    )


def seats_left(cohort: Cohort, *, now: dt.datetime | None = None) -> int:
    return max(0, cohort.capacity - holding_seats(cohort, now=now).count())


def hold_is_live(enrolment: Enrolment, *, now: dt.datetime | None = None) -> bool:
    return bool(enrolment.hold_expires_at and enrolment.hold_expires_at > (now or timezone.now()))


def upcoming_cohorts(course: Any, *, today: dt.date) -> QuerySet[Cohort]:
    """Cohorts a visitor can see: open or full, and not started yet."""
    return course.cohorts.filter(
        status__in=[CohortStatus.OPEN, CohortStatus.FULL], starts_on__gt=today
    ).order_by("starts_on")


def _refresh_cohort(cohort: Cohort) -> None:
    """Recount paid seats and move the cohort between open and full."""
    count = Enrolment.objects.filter(cohort=cohort, status__in=SEATED_STATUSES).count()
    cohort.enrolled_count = count
    if cohort.status == CohortStatus.OPEN and count >= cohort.capacity:
        cohort.status = CohortStatus.FULL
    elif cohort.status == CohortStatus.FULL and count < cohort.capacity:
        cohort.status = CohortStatus.OPEN
    cohort.save(update_fields=["enrolled_count", "status", "updated_at"])
    if count > cohort.capacity:
        # A payment that settled after its hold lapsed, into a cohort that had
        # filled meanwhile. The student has paid; a person must decide.
        logger.critical(
            "cohort_overbooked",
            extra={"cohort": str(cohort.pk), "enrolled": count, "capacity": cohort.capacity},
        )


# ──────────────────────────────────────────────────────────────────────────────
# Enrolling and paying
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def enrol(
    *,
    cohort_id: Any,
    name: str,
    email: str,
    phone: str,
    experience_level: str,
    payment_method: str,
    user: Any = None,
    expected_amount: int | None = None,
    idempotency_key: str = "",
) -> Enrolment:
    """Take a seat in a cohort (ACA-4).

    The cohort row is locked while seats are counted, so two people cannot take
    the last seat. The seat is held until payment or until the hold lapses.
    """
    cohort = (
        Cohort.objects.select_for_update()
        .select_related("course__branch", "course__instructor")
        .filter(pk=cohort_id, course__is_active=True)
        .first()
    )
    if cohort is None:
        raise Http404
    course = cohort.course
    branch = course.branch
    now = timezone.now()

    if cohort.status != CohortStatus.OPEN or cohort.starts_on <= branch.local_now().date():
        raise CohortUnavailable("Choose another start date.")
    if seats_left(cohort, now=now) <= 0:
        raise CohortFull("Every seat in this class is taken. Choose another start date.")
    if payment_method == EnrolmentPaymentMethod.TRANSFER and not branch.accepts_bank_transfer:
        raise TransferUnavailable("Please pay by card.")
    if expected_amount is not None and expected_amount != course.price:
        from apps.carts.serializers import money

        raise PriceChanged(
            "The course fee has changed. Please review it before enrolling.",
            price=money(course.price),
        )
    normalised_email = email.strip().lower()
    if holding_seats(cohort, now=now).filter(email__iexact=normalised_email).exists():
        raise AlreadyEnrolled("Check your email for your enrolment details.")

    hold = (
        dt.timedelta(minutes=settings.ACADEMY_CARD_HOLD_MINUTES)
        if payment_method == EnrolmentPaymentMethod.CARD
        else dt.timedelta(hours=settings.ACADEMY_TRANSFER_HOLD_HOURS)
    )
    enrolment = Enrolment.objects.create(
        course=course,
        cohort=cohort,
        user=user,
        name=name.strip(),
        email=normalised_email,
        phone=phone.strip(),
        experience_level=experience_level,
        payment_method=payment_method,
        amount=course.price,
        currency=branch.currency,
        hold_expires_at=now + hold,
        idempotency_key=idempotency_key[:64],
    )
    if payment_method == EnrolmentPaymentMethod.TRANSFER:
        _notify_transfer(enrolment)
    return enrolment


def ensure_payable(enrolment: Enrolment) -> None:
    if (
        enrolment.status != EnrolmentStatus.PENDING_PAYMENT
        or enrolment.payment_method != EnrolmentPaymentMethod.CARD
    ):
        raise EnrolmentNotPayable("There is nothing to pay online for this enrolment.")
    if not hold_is_live(enrolment):
        raise EnrolmentExpired("Your seat hold has expired. Please enrol again.")


def confirm_payment(enrolment: Enrolment, record: Any) -> Enrolment:
    """Mark an enrolment paid. Called from payment settlement, inside its transaction."""
    enrolment = Enrolment.objects.select_for_update().get(pk=enrolment.pk)
    if enrolment.paid_at is not None:
        return enrolment

    now = timezone.now()
    enrolment.amount_paid = record.amount_verified or record.amount
    enrolment.paid_at = now
    if enrolment.status == EnrolmentStatus.CANCELLED:
        enrolment.save(update_fields=["amount_paid", "paid_at", "updated_at"])
        logger.critical("payment_for_cancelled_enrolment", extra={"enrolment": enrolment.reference})
        return enrolment

    enrolment.status = EnrolmentStatus.CONFIRMED
    enrolment.hold_expires_at = None
    enrolment.save(
        update_fields=["amount_paid", "paid_at", "status", "hold_expires_at", "updated_at"]
    )
    _refresh_cohort(Cohort.objects.select_for_update().get(pk=enrolment.cohort_id))
    _notify_confirmed(enrolment)
    return enrolment


@transaction.atomic
def record_transfer(*, enrolment: Enrolment, actor: Any = None) -> Enrolment:
    """Staff confirm a bank transfer arrived. Recorded in the same payment ledger."""
    from apps.payments.models import PaymentTransaction, Provider, TransactionStatus
    from apps.payments.services.payments import build_reference

    if enrolment.status != EnrolmentStatus.PENDING_PAYMENT or enrolment.paid_at:
        raise EnrolmentStateError("Only an unpaid enrolment can have a transfer recorded.")
    record = PaymentTransaction.objects.create(
        enrolment=enrolment,
        provider=Provider.BANK_TRANSFER,
        our_reference=build_reference(enrolment),
        amount=enrolment.amount,
        amount_verified=enrolment.amount,
        currency=enrolment.currency,
        status=TransactionStatus.SUCCESS,
        verified_at=timezone.now(),
        channel="bank",
    )
    logger.info(
        "enrolment_transfer_recorded",
        extra={"enrolment": enrolment.reference, "actor": str(getattr(actor, "pk", ""))},
    )
    return confirm_payment(enrolment, record)


@transaction.atomic
def cancel_enrolment(*, enrolment: Enrolment, reason: str = "") -> Enrolment:
    """Staff cancel. A paid fee is refunded offline and the seat is released."""
    if enrolment.status in {EnrolmentStatus.CANCELLED, EnrolmentStatus.COMPLETED}:
        raise EnrolmentStateError("This enrolment is already closed.")
    enrolment.status = EnrolmentStatus.CANCELLED
    enrolment.cancelled_at = timezone.now()
    enrolment.cancellation_reason = reason
    enrolment.hold_expires_at = None
    enrolment.save()
    _refresh_cohort(Cohort.objects.select_for_update().get(pk=enrolment.cohort_id))
    return enrolment


@transaction.atomic
def complete_enrolment(*, enrolment: Enrolment) -> Enrolment:
    """The student finished the course: mark it and issue the certificate."""
    if enrolment.status != EnrolmentStatus.CONFIRMED:
        raise EnrolmentStateError("Only a confirmed enrolment can be completed.")
    now = timezone.now()
    enrolment.status = EnrolmentStatus.COMPLETED
    enrolment.completed_at = now
    enrolment.certificate_issued_at = now
    enrolment.save()
    _notify_certificate(enrolment)
    return enrolment


# ──────────────────────────────────────────────────────────────────────────────
# Emails
# ──────────────────────────────────────────────────────────────────────────────


def manage_url(enrolment: Enrolment) -> str:
    """Link to the enrolment page. Guests need the token; account holders sign in."""
    url = f"{settings.FRONTEND_URL}/academy/enrolments/{enrolment.reference}"
    return url if enrolment.user_id else f"{url}?token={enrolment.guest_token}"


def _long_date(day: dt.date) -> str:
    return f"{day.day} {day:%B %Y}"


def _notify_confirmed(enrolment: Enrolment) -> None:
    from apps.notifications.services import queue_templated_email

    cohort = enrolment.cohort
    queue_templated_email(
        template_key="enrolment_confirmed",
        recipient=enrolment.email,
        context={
            "name": enrolment.name.split(" ")[0] or "there",
            "reference": enrolment.reference,
            "course": enrolment.course.title,
            "instructor": enrolment.course.instructor.name,
            "starts_on": _long_date(cohort.starts_on),
            "ends_on": _long_date(cohort.ends_on),
            "schedule_line": f"Schedule:   {cohort.schedule_note}\n"
            if cohort.schedule_note
            else "",
            "amount": format_money(enrolment.amount_paid, enrolment.currency),
            "manage_url": manage_url(enrolment),
        },
    )


def _notify_transfer(enrolment: Enrolment) -> None:
    from apps.notifications.services import queue_templated_email

    branch = enrolment.course.branch
    hold_until = timezone.localtime(enrolment.hold_expires_at, timezone=branch.tzinfo())
    queue_templated_email(
        template_key="enrolment_transfer_details",
        recipient=enrolment.email,
        context={
            "name": enrolment.name.split(" ")[0] or "there",
            "course": enrolment.course.title,
            "reference": enrolment.reference,
            "amount": format_money(enrolment.amount, enrolment.currency),
            "bank_name": branch.bank_name,
            "account_name": branch.bank_account_name,
            "account_number": branch.bank_account_number,
            "hold_until": f"{hold_until:%H:%M} on {_long_date(hold_until.date())}",
            "manage_url": manage_url(enrolment),
        },
    )


def _notify_certificate(enrolment: Enrolment) -> None:
    from apps.notifications.services import queue_templated_email

    queue_templated_email(
        template_key="enrolment_certificate",
        recipient=enrolment.email,
        context={
            "name": enrolment.name.split(" ")[0] or "there",
            "course": enrolment.course.title,
            "manage_url": manage_url(enrolment),
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Certificates
# ──────────────────────────────────────────────────────────────────────────────


def certificate_pdf(enrolment: Enrolment) -> bytes:
    """A one-page landscape certificate. Only for an issued certificate."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    if enrolment.certificate_issued_at is None:
        raise CertificateNotAvailable("It is issued when you complete the course.")

    width, height = landscape(A4)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    pdf.setTitle(f"Certificate {enrolment.reference}")
    pdf.setLineWidth(2)
    pdf.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm)

    def centre(text: str, y: float, size: float, font: str = "Helvetica") -> None:
        pdf.setFont(font, size)
        pdf.drawCentredString(width / 2, y, text)

    issued = timezone.localtime(
        enrolment.certificate_issued_at, timezone=enrolment.course.branch.tzinfo()
    )
    cohort = enrolment.cohort
    centre("KUYASH ACADEMY", height - 45 * mm, 14, "Helvetica-Bold")
    centre("Certificate of Completion", height - 65 * mm, 30, "Helvetica-Bold")
    centre("This certifies that", height - 85 * mm, 12)
    centre(enrolment.name, height - 102 * mm, 26, "Helvetica-Bold")
    centre("has successfully completed", height - 118 * mm, 12)
    centre(enrolment.course.title, height - 133 * mm, 18, "Helvetica-Bold")
    centre(
        f"{_long_date(cohort.starts_on)} – {_long_date(cohort.ends_on)}"
        f" · Instructor: {enrolment.course.instructor.name}",
        height - 146 * mm,
        11,
    )
    centre(
        f"Issued {_long_date(issued.date())} · Reference {enrolment.reference}",
        26 * mm,
        9,
    )
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
