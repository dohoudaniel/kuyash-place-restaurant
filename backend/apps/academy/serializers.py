"""Academy serializers."""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.academy import services
from apps.academy.models import (
    Cohort,
    CohortStatus,
    Course,
    CourseLevel,
    CourseType,
    Enrolment,
    EnrolmentPaymentMethod,
    EnrolmentStatus,
    ExperienceLevel,
    Instructor,
)
from apps.carts.serializers import money
from apps.common.fields import phone_validator
from apps.common.serializers import MoneySerializer
from apps.core.serializers import BankTransferSerializer


def _image_url(image: Any) -> str | None:
    return image.url if image else None


class InstructorSummarySerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Instructor
        fields: tuple[str, ...] = ("name", "photo_url")
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj: Instructor) -> str | None:
        return _image_url(obj.photo)


class InstructorSerializer(InstructorSummarySerializer):
    specialities = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta(InstructorSummarySerializer.Meta):
        fields = (*InstructorSummarySerializer.Meta.fields, "bio", "specialities")
        read_only_fields = fields


class CohortSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=CohortStatus.choices, read_only=True)
    seats_left = serializers.SerializerMethodField()

    class Meta:
        model = Cohort
        fields = ("id", "starts_on", "ends_on", "schedule_note", "capacity", "seats_left", "status")
        read_only_fields = fields

    def get_seats_left(self, obj: Cohort) -> int:
        if obj.status != CohortStatus.OPEN:
            return 0
        return services.seats_left(obj, now=self.context.get("now"))


class CourseSerializer(serializers.ModelSerializer):
    level = serializers.ChoiceField(choices=CourseLevel.choices, read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)
    type = serializers.ChoiceField(source="course_type", choices=CourseType.choices, read_only=True)
    type_display = serializers.CharField(source="get_course_type_display", read_only=True)
    price = serializers.SerializerMethodField()
    features = serializers.ListField(child=serializers.CharField(), read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    instructor = InstructorSummarySerializer(read_only=True)
    student_count = serializers.SerializerMethodField()
    next_cohort = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields: tuple[str, ...] = (
            "slug",
            "title",
            "description",
            "level",
            "level_display",
            "type",
            "type_display",
            "duration_label",
            "session_count",
            "price",
            "features",
            "thumbnail_url",
            "instructor",
            "student_count",
            "next_cohort",
        )
        read_only_fields = fields

    @extend_schema_field(MoneySerializer)
    def get_price(self, obj: Course) -> dict[str, Any]:
        return money(obj.price, obj.branch.currency)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_thumbnail_url(self, obj: Course) -> str | None:
        return _image_url(obj.thumbnail)

    def get_student_count(self, obj: Course) -> int:
        """Counted from paid enrolments (ACA-8), never typed in."""
        return int(getattr(obj, "student_count", 0) or 0)

    def _upcoming(self, obj: Course) -> list[Cohort]:
        cached = getattr(obj, "upcoming_cohorts", None)
        if cached is not None:
            return list(cached)
        today: dt.date = self.context.get("today") or obj.branch.local_now().date()
        return list(services.upcoming_cohorts(obj, today=today))

    @extend_schema_field(CohortSerializer(allow_null=True))
    def get_next_cohort(self, obj: Course) -> dict[str, Any] | None:
        """The soonest class with a free seat, or else the soonest class."""
        cohorts = self._upcoming(obj)
        if not cohorts:
            return None
        rendered = CohortSerializer(cohorts, many=True, context=self.context).data
        return next((row for row in rendered if row["seats_left"] > 0), rendered[0])


class CourseDetailSerializer(CourseSerializer):
    instructor = InstructorSerializer(read_only=True)
    cohorts = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = (*CourseSerializer.Meta.fields, "cohorts")
        read_only_fields = fields

    @extend_schema_field(CohortSerializer(many=True))
    def get_cohorts(self, obj: Course) -> list[dict[str, Any]]:
        return list(CohortSerializer(self._upcoming(obj), many=True, context=self.context).data)


class EnrolmentCourseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()
    instructor = serializers.CharField()

    class Meta:
        ref_name = "EnrolmentCourse"


class EnrolmentSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=EnrolmentStatus.choices, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    experience_level = serializers.ChoiceField(choices=ExperienceLevel.choices, read_only=True)
    payment_method = serializers.ChoiceField(choices=EnrolmentPaymentMethod.choices, read_only=True)
    course = serializers.SerializerMethodField()
    cohort = CohortSerializer(read_only=True)
    amount = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()
    certificate_available = serializers.SerializerMethodField()
    bank_transfer = serializers.SerializerMethodField()

    class Meta:
        model = Enrolment
        fields = (
            "reference",
            "status",
            "status_display",
            "course",
            "cohort",
            "name",
            "email",
            "phone",
            "experience_level",
            "payment_method",
            "amount",
            "amount_paid",
            "hold_expires_at",
            "paid_at",
            "completed_at",
            "can_pay",
            "certificate_available",
            "bank_transfer",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(EnrolmentCourseSerializer)
    def get_course(self, obj: Enrolment) -> dict[str, str]:
        return {
            "slug": obj.course.slug,
            "title": obj.course.title,
            "instructor": obj.course.instructor.name,
        }

    @extend_schema_field(MoneySerializer)
    def get_amount(self, obj: Enrolment) -> dict[str, Any]:
        return money(obj.amount, obj.currency)

    @extend_schema_field(MoneySerializer)
    def get_amount_paid(self, obj: Enrolment) -> dict[str, Any]:
        return money(obj.amount_paid, obj.currency)

    def get_can_pay(self, obj: Enrolment) -> bool:
        return (
            obj.status == EnrolmentStatus.PENDING_PAYMENT
            and obj.payment_method == EnrolmentPaymentMethod.CARD
            and services.hold_is_live(obj, now=timezone.now())
        )

    def get_certificate_available(self, obj: Enrolment) -> bool:
        return obj.certificate_issued_at is not None

    @extend_schema_field(BankTransferSerializer(allow_null=True))
    def get_bank_transfer(self, obj: Enrolment) -> dict[str, str] | None:
        """Where to send the fee, while a transfer enrolment is still unpaid."""
        branch = obj.course.branch
        if (
            obj.payment_method != EnrolmentPaymentMethod.TRANSFER
            or obj.status != EnrolmentStatus.PENDING_PAYMENT
            or not branch.accepts_bank_transfer
        ):
            return None
        return {
            "bank_name": branch.bank_name,
            "account_name": branch.bank_account_name,
            "account_number": branch.bank_account_number,
        }


class EnrolmentCreateSerializer(serializers.Serializer):
    cohort = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, validators=[phone_validator])
    experience_level = serializers.ChoiceField(choices=ExperienceLevel.choices)
    payment_method = serializers.ChoiceField(choices=EnrolmentPaymentMethod.choices)
    expected_amount = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="The course fee the student was shown, in kobo. A guard, not a price.",
    )


class PaymentStartSerializer(serializers.Serializer):
    reference = serializers.CharField()
    authorization_url = serializers.URLField()

    class Meta:
        ref_name = "EnrolmentPaymentStart"


class EnrolmentCreatedSerializer(serializers.Serializer):
    enrolment = EnrolmentSerializer()
    payment = PaymentStartSerializer(allow_null=True)
    payment_error = serializers.CharField(
        allow_blank=True, help_text="Why the card payment could not be started; retry with /pay/."
    )
    guest_token = serializers.CharField(
        required=False, help_text="Guests only. Send as X-Enrolment-Token."
    )


class EnrolmentVerificationSerializer(serializers.Serializer):
    status = serializers.CharField()
    enrolment_reference = serializers.CharField()
    enrolment_status = serializers.ChoiceField(choices=EnrolmentStatus.choices)

    class Meta:
        ref_name = "EnrolmentPaymentVerification"
