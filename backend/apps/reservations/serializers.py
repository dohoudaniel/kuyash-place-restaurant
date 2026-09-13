"""Reservation serializers."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.common.serializers import MoneyField
from apps.reservations.models import Reservation, TableArea


class TableAreaSerializer(serializers.ModelSerializer):
    surcharge = MoneyField()

    class Meta:
        model = TableArea
        fields = ("id", "slug", "name", "description", "features", "is_premium", "surcharge")
        read_only_fields = fields


class SlotSerializer(serializers.Serializer):
    time = serializers.CharField()
    available = serializers.BooleanField()
    tables_left = serializers.IntegerField()
    reason = serializers.CharField(required=False)

    class Meta:
        ref_name = "ReservationSlot"


class AvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    party_size = serializers.IntegerField()
    area = serializers.CharField(allow_blank=True)
    slots = SlotSerializer(many=True)

    class Meta:
        ref_name = "ReservationAvailability"


class CreateReservationSerializer(serializers.Serializer):
    """Input for booking. Mirrors the fields the frontend wizard already collects."""

    area = serializers.SlugField()
    date = serializers.DateField()
    time = serializers.TimeField()
    party_size = serializers.IntegerField(min_value=1, max_value=50)
    guest_name = serializers.CharField(max_length=150)
    guest_email = serializers.EmailField()
    guest_phone = serializers.CharField(max_length=20)
    special_requests = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )


class RescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    time = serializers.TimeField()
    party_size = serializers.IntegerField(min_value=1, max_value=50, required=False)


class CancelReservationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=300)


class ReservationSerializer(serializers.ModelSerializer):
    """A booking as the customer sees it."""

    area = TableAreaSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    table_number = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields: tuple[str, ...] = (
            "reference",
            "status",
            "status_display",
            "area",
            "table_number",
            "reserved_for",
            "ends_at",
            "duration_minutes",
            "party_size",
            "guest_name",
            "guest_email",
            "guest_phone",
            "special_requests",
            "can_cancel",
            "created_at",
        )
        read_only_fields = fields

    def get_table_number(self, obj: Reservation) -> str:
        return obj.table.number if obj.table else ""


def serialise_with_token(reservation: Reservation) -> dict[str, Any]:
    """Booking payload including the guest's management token."""
    data = dict(ReservationSerializer(reservation).data)
    data["confirmation_token"] = reservation.confirmation_token
    return data


class BookedReservationSerializer(ReservationSerializer):
    """A reservation as it appears in the day's book, with local time added."""

    time = serializers.CharField(read_only=True, help_text="Local HH:MM.")

    class Meta(ReservationSerializer.Meta):
        fields = (*ReservationSerializer.Meta.fields, "time")


class TodaysBookSerializer(serializers.Serializer):
    """Response envelope for ``GET /reservations/book/``.

    Declared explicitly so the generated OpenAPI schema — and the frontend types
    generated from it — describe this endpoint instead of omitting it.
    """

    date = serializers.DateField()
    covers = serializers.IntegerField()
    reservations = BookedReservationSerializer(many=True)
