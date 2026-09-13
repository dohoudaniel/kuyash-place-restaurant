"""Reservation endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import idempotency
from apps.common.exceptions import DomainError
from apps.common.permissions import IsStaffMember, current_user
from apps.core.selectors import get_current_branch
from apps.reservations.models import Reservation, TableArea
from apps.reservations.serializers import (
    AvailabilitySerializer,
    CancelReservationSerializer,
    CreateReservationSerializer,
    RescheduleSerializer,
    ReservationSerializer,
    TableAreaSerializer,
    TodaysBookSerializer,
    serialise_with_token,
)
from apps.reservations.services import booking
from apps.reservations.services.availability import slots_for

GUEST_TOKEN_HEADER = "X-Reservation-Token"  # noqa: S105 - a header name, not a credential


class MissingIdempotencyKey(DomainError):
    code = "idempotency_key_required"
    title = "An Idempotency-Key header is required"
    status_code = status.HTTP_400_BAD_REQUEST


def _may_access(request: Request, reservation: Reservation) -> bool:
    user = request.user
    if user.is_authenticated:
        if reservation.user_id and reservation.user_id == user.pk:
            return True
        if user.is_staff or user.groups.filter(name__in=["managers", "kitchen"]).exists():
            return True
    supplied = request.headers.get(GUEST_TOKEN_HEADER, "") or request.query_params.get("token", "")
    return bool(supplied) and constant_time_compare(reservation.confirmation_token, supplied)


class AreaListView(ListAPIView):
    """Seating areas."""

    permission_classes = [AllowAny]
    serializer_class = TableAreaSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return TableArea.objects.filter(branch=get_current_branch(), is_active=True)

    @extend_schema(summary="List seating areas", tags=["reservations"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class AvailabilityView(APIView):
    """Real availability for a date.

    Every slot carries a reason when it is unavailable, so the UI can say
    "fully booked" rather than silently greying a button out.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reservation availability",
        responses={200: AvailabilitySerializer},
        parameters=[
            OpenApiParameter("date", str, description="YYYY-MM-DD."),
            OpenApiParameter("party_size", int, description="Number of guests."),
            OpenApiParameter("area", str, description="Area slug. Omit for any area."),
        ],
        tags=["reservations"],
    )
    def get(self, request: Request) -> Response:
        branch = get_current_branch()
        raw_date = request.query_params.get("date", "")
        try:
            date = dt.date.fromisoformat(raw_date)
        except ValueError:
            date = branch.local_now().date()

        try:
            party_size = max(int(request.query_params.get("party_size", 2)), 1)
        except (TypeError, ValueError):
            party_size = 2

        area_slug = request.query_params.get("area", "")
        area = (
            TableArea.objects.filter(branch=branch, slug=area_slug, is_active=True).first()
            if area_slug
            else None
        )

        slots = slots_for(branch, date=date, party_size=party_size, area=area)
        return Response(
            {
                "date": date.isoformat(),
                "party_size": party_size,
                "area": area.slug if area else "",
                "slots": [slot.as_dict() for slot in slots],
            }
        )


class ReservationCreateView(APIView):
    """Book a table."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Book a table",
        request=CreateReservationSerializer,
        responses={201: ReservationSerializer},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                str,
                OpenApiParameter.HEADER,
                required=True,
                description="A UUID. Replaying it returns the original booking.",
            )
        ],
        tags=["reservations"],
    )
    def post(self, request: Request) -> Response:
        key = request.headers.get(idempotency.HEADER, "").strip()
        if not key:
            raise MissingIdempotencyKey(
                "Send an Idempotency-Key header so a repeated submission cannot book two tables."
            )

        serializer = CreateReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cache_key, replayed = idempotency.begin("reservations", key, request.data)
        if replayed is not None:
            response = Response(replayed, status=status.HTTP_201_CREATED)
            response["Idempotency-Replayed"] = "true"
            return response

        branch = get_current_branch()
        area = get_object_or_404(TableArea, branch=branch, slug=data["area"], is_active=True)
        reserved_for = dt.datetime.combine(data["date"], data["time"], tzinfo=branch.tzinfo())

        try:
            reservation = booking.book(
                branch=branch,
                area=area,
                reserved_for=reserved_for,
                party_size=data["party_size"],
                guest_name=data["guest_name"],
                guest_email=data["guest_email"],
                guest_phone=data["guest_phone"],
                user=request.user,
                special_requests=data.get("special_requests", ""),
                idempotency_key=key,
            )
        except Exception:
            idempotency.abandon(cache_key)
            raise

        body = serialise_with_token(reservation)
        idempotency.complete(cache_key, body)
        return Response(body, status=status.HTTP_201_CREATED)


class ReservationDetailView(APIView):
    """View, reschedule or cancel one booking."""

    permission_classes = [AllowAny]

    def _get(self, request: Request, reference: str) -> Reservation | None:
        reservation = get_object_or_404(
            Reservation.objects.select_related("area", "table", "branch"), reference=reference
        )
        return reservation if _may_access(request, reservation) else None

    @extend_schema(
        summary="Retrieve a booking",
        responses={200: ReservationSerializer},
        parameters=[
            OpenApiParameter(
                GUEST_TOKEN_HEADER,
                str,
                OpenApiParameter.HEADER,
                description="Required for guest bookings.",
            )
        ],
        tags=["reservations"],
    )
    def get(self, request: Request, reference: str) -> Response:
        reservation = self._get(request, reference)
        if reservation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ReservationSerializer(reservation).data)

    @extend_schema(
        summary="Reschedule a booking",
        request=RescheduleSerializer,
        responses={200: ReservationSerializer},
        tags=["reservations"],
    )
    def patch(self, request: Request, reference: str) -> Response:
        reservation = self._get(request, reference)
        if reservation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reserved_for = dt.datetime.combine(
            data["date"], data["time"], tzinfo=reservation.branch.tzinfo()
        )
        booking.reschedule(
            reservation=reservation,
            reserved_for=reserved_for,
            party_size=data.get("party_size"),
        )
        reservation.refresh_from_db()
        return Response(ReservationSerializer(reservation).data)


class ReservationCancelView(APIView):
    """Cancel a booking and free the table."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Cancel a booking",
        request=CancelReservationSerializer,
        responses={200: ReservationSerializer},
        tags=["reservations"],
    )
    def post(self, request: Request, reference: str) -> Response:
        reservation = get_object_or_404(Reservation, reference=reference)
        if not _may_access(request, reservation):
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = CancelReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.cancel(reservation=reservation, reason=serializer.validated_data.get("reason", ""))
        reservation.refresh_from_db()
        return Response(ReservationSerializer(reservation).data)


class MyReservationsView(ListAPIView):
    """The signed-in customer's bookings."""

    permission_classes = [IsAuthenticated]
    serializer_class = ReservationSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Reservation.objects.filter(user=current_user(self.request)).select_related(
            "area", "table"
        )

    @extend_schema(summary="My bookings", tags=["reservations"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class TodaysBookView(APIView):
    """The day's reservations, for staff.

    Front-of-house needs one screen showing who is coming and when.
    """

    permission_classes = [IsStaffMember]

    @extend_schema(
        summary="Today's book",
        responses={200: TodaysBookSerializer},
        tags=["reservations"],
    )
    def get(self, request: Request) -> Response:
        branch = get_current_branch()
        raw_date = request.query_params.get("date", "")
        try:
            date = dt.date.fromisoformat(raw_date)
        except ValueError:
            date = branch.local_now().date()

        start = dt.datetime.combine(date, dt.time.min, tzinfo=branch.tzinfo())
        end = start + dt.timedelta(days=1)
        bookings = (
            Reservation.objects.filter(branch=branch, reserved_for__gte=start, reserved_for__lt=end)
            .select_related("area", "table")
            .order_by("reserved_for")
        )
        return Response(
            {
                "date": date.isoformat(),
                "covers": sum(b.party_size for b in bookings if b.occupies_a_table),
                "reservations": [
                    {
                        **ReservationSerializer(b).data,
                        "time": b.reserved_for.astimezone(branch.tzinfo()).strftime("%H:%M"),
                    }
                    for b in bookings
                ],
            }
        )
