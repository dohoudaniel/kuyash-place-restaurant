"""Kuyash Academy: instructors, courses, cohorts and enrolments.

Replaces a ``COURSES`` array inside ``app/academy/page.tsx`` — instructor names,
ratings and student counts typed in by hand — and an enrolment form whose
submit handler was ``alert("Enrollment submitted successfully!")`` for courses
costing up to ₦150,000. The start date was free text and the form offered
"installment" payments with no ledger behind them (ACA-6); that option is not
represented here and has been removed from the UI (OD-5).
"""

from __future__ import annotations

import secrets

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

from apps.common.fields import MoneyField, PhoneField
from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.gallery.models import IMAGE_EXTENSIONS, validate_image_size

REFERENCE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
REFERENCE_PREFIX = "ACA-"
IMAGE_VALIDATORS = [FileExtensionValidator(IMAGE_EXTENSIONS), validate_image_size]


def generate_reference() -> str:
    for _ in range(12):
        candidate = REFERENCE_PREFIX + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
        if not Enrolment.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Could not allocate an enrolment reference.")  # pragma: no cover


def generate_guest_token() -> str:
    return secrets.token_urlsafe(32)


class CourseLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    MASTERCLASS = "masterclass", "Masterclass"


class CourseType(models.TextChoices):
    COOKING = "cooking", "Cooking"
    BAKING = "baking", "Baking"
    PLATING = "plating", "Plating"
    BUSINESS = "business", "Business"
    NUTRITION = "nutrition", "Nutrition"


class CohortStatus(models.TextChoices):
    OPEN = "open", "Open for enrolment"
    FULL = "full", "Full"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class EnrolmentStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Awaiting payment"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class EnrolmentPaymentMethod(models.TextChoices):
    CARD = "card", "Card"
    TRANSFER = "transfer", "Bank transfer"


#: Statuses that occupy a seat for good.
SEATED_STATUSES = (EnrolmentStatus.CONFIRMED, EnrolmentStatus.COMPLETED)


class Instructor(TimeStampedModel, SoftDeleteModel):
    """A first-class instructor (ACA-2), not a string on each course."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instructor_profiles",
    )
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="academy/instructors/", null=True, blank=True, validators=IMAGE_VALIDATORS
    )
    specialities = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Course(TimeStampedModel, SoftDeleteModel):
    branch = models.ForeignKey("core.Branch", on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField()
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="courses")
    level = models.CharField(max_length=20, choices=CourseLevel.choices)
    course_type = models.CharField(max_length=20, choices=CourseType.choices)
    duration_label = models.CharField(max_length=60, help_text='e.g. "4 weeks".')
    session_count = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    price = MoneyField(help_text="Course fee in kobo.")
    features = models.JSONField(default=list, blank=True)
    thumbnail = models.ImageField(
        upload_to="academy/courses/", null=True, blank=True, validators=IMAGE_VALIDATORS
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "title"]

    def __str__(self) -> str:
        return self.title


class Cohort(TimeStampedModel):
    """One run of a course, with real dates and a real capacity (ACA-3)."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="cohorts")
    starts_on = models.DateField()
    ends_on = models.DateField()
    capacity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    enrolled_count = models.PositiveSmallIntegerField(
        default=0, editable=False, help_text="Paid seats. Maintained by the enrolment service."
    )
    schedule_note = models.CharField(
        max_length=200, blank=True, help_text='e.g. "Saturdays, 10:00–14:00".'
    )
    status = models.CharField(
        max_length=20, choices=CohortStatus.choices, default=CohortStatus.OPEN, db_index=True
    )

    class Meta:
        ordering = ["starts_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="cohort_ends_after_it_starts",
            )
        ]

    def __str__(self) -> str:
        return f"{self.course.title} — {self.starts_on:%d %b %Y}"


class Enrolment(TimeStampedModel):
    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="enrolments")
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name="enrolments")
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrolments",
    )

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = PhoneField()
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices)

    status = models.CharField(
        max_length=20,
        choices=EnrolmentStatus.choices,
        default=EnrolmentStatus.PENDING_PAYMENT,
        db_index=True,
    )
    payment_method = models.CharField(max_length=20, choices=EnrolmentPaymentMethod.choices)
    amount = MoneyField(help_text="The course fee when the student enrolled, in kobo.")
    amount_paid = MoneyField()
    currency = models.CharField(max_length=3, default="NGN")

    hold_expires_at = models.DateTimeField(
        null=True, blank=True, help_text="An unpaid enrolment holds its seat until this moment."
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)

    guest_token = models.CharField(max_length=64, default=generate_guest_token, editable=False)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # See Order: the database is the backstop when the cache is not there.
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_enrolment_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["cohort", "status"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.name}"
