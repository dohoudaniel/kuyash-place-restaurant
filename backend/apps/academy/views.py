"""Academy endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db.models import Count, Prefetch, Q, QuerySet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academy import services
from apps.academy.models import (
    SEATED_STATUSES,
    Cohort,
    CohortStatus,
    Course,
    CourseLevel,
    CourseType,
    Enrolment,
    EnrolmentStatus,
)
from apps.academy.serializers import (
    CohortSerializer,
    CourseDetailSerializer,
    CourseSerializer,
    EnrolmentCreatedSerializer,
    EnrolmentCreateSerializer,
    EnrolmentSerializer,
    EnrolmentVerificationSerializer,
    PaymentStartSerializer,
)
from apps.accounts.views import CsrfEnforcedMixin
from apps.common import idempotency
from apps.common.exceptions import DomainError, PaymentFailed
from apps.common.permissions import current_user, in_group
from apps.common.throttling import SCOPED_THROTTLES
from apps.core.selectors import get_current_branch

ENROLMENT_TOKEN_HEADER = "X-Enrolment-Token"  # noqa: S105 - a header name, not a credential


class MissingIdempotencyKey(DomainError):
    code = "idempotency_key_required"
    title = "An Idempotency-Key header is required"
    status_code = status.HTTP_400_BAD_REQUEST


def _seats_taken(now: dt.datetime) -> Count:
    """Seats a cohort has given away: paid ones, plus holds that are still live.

    One aggregate across the whole page. ``CohortSerializer`` used to ask
    ``services.seats_left`` per cohort — a ``COUNT(*)`` each, three per course,
    on a course list with no pagination.
    """
    return Count(
        "enrolments",
        filter=Q(enrolments__status__in=SEATED_STATUSES)
        | Q(
            enrolments__status=EnrolmentStatus.PENDING_PAYMENT,
            enrolments__hold_expires_at__gt=now,
        ),
    )


def _courses(*, today: dt.date, now: dt.datetime) -> QuerySet[Course]:
    return (
        Course.objects.filter(branch=get_current_branch(), is_active=True)
        .select_related("instructor", "branch")
        .annotate(
            student_count=Count("enrolments", filter=Q(enrolments__status__in=SEATED_STATUSES))
        )
        .prefetch_related(
            Prefetch(
                "cohorts",
                queryset=Cohort.objects.filter(
                    status__in=[CohortStatus.OPEN, CohortStatus.FULL], starts_on__gt=today
                )
                .annotate(seats_taken=_seats_taken(now))
                .order_by("starts_on"),
                to_attr="upcoming_cohorts",
            )
        )
    )


def _context() -> dict[str, Any]:
    branch = get_current_branch()
    return {"today": branch.local_now().date(), "now": timezone.now()}


class CourseListView(ListAPIView):
    """Published courses. Not paginated: an academy offers a handful."""

    permission_classes = [AllowAny]
    serializer_class = CourseSerializer
    pagination_class = None

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), **_context()}

    def get_queryset(self) -> Any:
        params = self.request.query_params
        queryset = _courses(**_context())
        for param, field, choices in (
            ("level", "level", CourseLevel.values),
            ("type", "course_type", CourseType.values),
        ):
            value = params.get(param, "")
            if value:
                if value not in choices:
                    raise serializers.ValidationError(
                        {param: [f"Choose one of: {', '.join(choices)}."]}
                    )
                queryset = queryset.filter(**{field: value})
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(instructor__name__icontains=search)
            )
        return queryset

    @extend_schema(
        summary="List courses",
        parameters=[
            OpenApiParameter("level", OpenApiTypes.STR, enum=CourseLevel.values, required=False),
            OpenApiParameter("type", OpenApiTypes.STR, enum=CourseType.values, required=False),
            OpenApiParameter("search", OpenApiTypes.STR, required=False),
        ],
        tags=["academy"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class CourseDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve a course with its upcoming classes",
        responses={200: CourseDetailSerializer},
        tags=["academy"],
    )
    def get(self, request: Request, slug: str) -> Response:
        context = _context()
        course = get_object_or_404(_courses(**context), slug=slug)
        return Response(CourseDetailSerializer(course, context=context).data)


class CourseCohortsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Upcoming classes for a course, with seats left",
        responses={200: CohortSerializer(many=True)},
        tags=["academy"],
    )
    def get(self, request: Request, slug: str) -> Response:
        context = _context()
        course = get_object_or_404(_courses(**context), slug=slug)
        return Response(
            CohortSerializer(course.upcoming_cohorts, many=True, context=context).data  # type: ignore[attr-defined]
        )


def may_access(request: Request, enrolment: Enrolment) -> bool:
    user = request.user
    if user.is_authenticated:
        if enrolment.user_id and enrolment.user_id == user.pk:
            return True
        if user.is_staff or in_group(user, "managers"):
            return True
    supplied = request.headers.get(ENROLMENT_TOKEN_HEADER, "")
    return bool(supplied) and constant_time_compare(enrolment.guest_token, supplied)


def _enrolment(request: Request, reference: str) -> Enrolment:
    enrolment = get_object_or_404(
        Enrolment.objects.select_related("course__instructor", "course__branch", "cohort"),
        reference=reference,
    )
    if not may_access(request, enrolment):
        from django.http import Http404

        raise Http404
    return enrolment


def _payment_start(enrolment: Enrolment) -> tuple[dict[str, str] | None, str]:
    from apps.payments.services.payments import initialise_enrolment_payment

    try:
        record = initialise_enrolment_payment(enrolment=enrolment)
    except PaymentFailed as exc:
        return None, str(exc.detail)
    return {"reference": record.our_reference, "authorization_url": record.authorization_url}, ""


class EnrolmentCreateView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "enrolment_create"

    @extend_schema(
        summary="Enrol in a class",
        description=(
            "Requires an Idempotency-Key. Holds a seat, then for card payments returns "
            "the provider's checkout URL. 409 `cohort_full`, `cohort_unavailable`, "
            "`already_enrolled`, `transfer_unavailable`, `price_changed`."
        ),
        request=EnrolmentCreateSerializer,
        responses={201: EnrolmentCreatedSerializer},
        tags=["academy"],
    )
    def post(self, request: Request) -> Response:
        key = request.headers.get(idempotency.HEADER, "").strip()
        if not key:
            raise MissingIdempotencyKey(
                "Send an Idempotency-Key header so a repeated submission cannot enrol twice."
            )
        serializer = EnrolmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cache_key, replayed = idempotency.begin("academy_enrol", key, request.data)
        if replayed is not None:
            response = Response(replayed, status=status.HTTP_201_CREATED)
            response["Idempotency-Replayed"] = "true"
            return response

        user = request.user if request.user.is_authenticated else None
        try:
            enrolment = services.enrol(
                cohort_id=data["cohort"],
                name=data["name"],
                email=data["email"],
                phone=data["phone"],
                experience_level=data["experience_level"],
                payment_method=data["payment_method"],
                user=user,
                expected_amount=data.get("expected_amount"),
                idempotency_key=key,
            )
        except Exception:
            idempotency.abandon(cache_key)
            raise

        payment, payment_error = (None, "")
        if enrolment.payment_method == "card":
            payment, payment_error = _payment_start(enrolment)

        body: dict[str, Any] = {
            "enrolment": EnrolmentSerializer(enrolment).data,
            "payment": payment,
            "payment_error": payment_error,
        }
        if user is None:
            body["guest_token"] = enrolment.guest_token
        idempotency.complete(cache_key, body)
        return Response(body, status=status.HTTP_201_CREATED)


class MyEnrolmentsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EnrolmentSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Enrolment.objects.filter(user=current_user(self.request)).select_related(
            "course__instructor", "course__branch", "cohort"
        )

    @extend_schema(summary="My enrolments", tags=["academy"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


TOKEN_PARAMETER = OpenApiParameter(
    ENROLMENT_TOKEN_HEADER,
    location=OpenApiParameter.HEADER,
    required=False,
    description="Guests only: the token returned when they enrolled.",
)


class EnrolmentDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve an enrolment",
        parameters=[TOKEN_PARAMETER],
        responses={200: EnrolmentSerializer},
        tags=["academy"],
    )
    def get(self, request: Request, reference: str) -> Response:
        return Response(EnrolmentSerializer(_enrolment(request, reference)).data)


class EnrolmentPayView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Start (or retry) the card payment for an enrolment",
        parameters=[TOKEN_PARAMETER],
        request=None,
        responses={201: PaymentStartSerializer},
        tags=["academy"],
    )
    def post(self, request: Request, reference: str) -> Response:
        from apps.payments.services.payments import initialise_enrolment_payment

        enrolment = _enrolment(request, reference)
        record = initialise_enrolment_payment(enrolment=enrolment)
        return Response(
            {"reference": record.our_reference, "authorization_url": record.authorization_url},
            status=status.HTTP_201_CREATED,
        )


class EnrolmentPaymentVerifyView(APIView):
    """Where the browser lands after paying. Asks the provider; trusts nothing sent."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify a course payment",
        responses={200: EnrolmentVerificationSerializer},
        tags=["academy"],
    )
    def get(self, request: Request, reference: str) -> Response:
        from apps.payments.services.payments import verify_by_reference

        record = verify_by_reference(reference)
        if record is None or record.enrolment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrolment = record.enrolment
        enrolment.refresh_from_db()
        return Response(
            {
                "status": record.status,
                "enrolment_reference": enrolment.reference,
                "enrolment_status": enrolment.status,
            }
        )


class CertificateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Download a certificate (PDF)",
        parameters=[TOKEN_PARAMETER],
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
        tags=["academy"],
    )
    def get(self, request: Request, reference: str) -> HttpResponse:
        enrolment = _enrolment(request, reference)
        response = HttpResponse(services.certificate_pdf(enrolment), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="kuyash-academy-certificate-{enrolment.reference}.pdf"'
        )
        return response
