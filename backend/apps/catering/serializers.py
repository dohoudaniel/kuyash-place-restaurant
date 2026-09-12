"""Catering serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.catering.models import CateringEnquiry, CateringPackage
from apps.common.serializers import MoneyField


class CateringPackageSerializer(serializers.ModelSerializer):
    price_per_person = MoneyField()

    class Meta:
        model = CateringPackage
        fields = (
            "id",
            "slug",
            "name",
            "description",
            "min_guests",
            "max_guests",
            "price_per_person",
            "features",
            "is_popular",
        )
        read_only_fields = fields


class CreateEnquirySerializer(serializers.Serializer):
    """Exactly the fields the existing form collects.

    Note what is absent: any price. The indicative total is computed server-side
    from the package and the guest count.
    """

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    guest_count = serializers.IntegerField(min_value=1, max_value=5000)
    package = serializers.SlugField(required=False, allow_blank=True, default="")
    event_type = serializers.CharField(required=False, allow_blank=True, default="", max_length=120)
    event_date = serializers.DateField(required=False, allow_null=True)
    event_time = serializers.TimeField(required=False, allow_null=True)
    venue = serializers.CharField(required=False, allow_blank=True, default="", max_length=255)
    message = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class EnquirySerializer(serializers.ModelSerializer):
    """What the customer gets back — never the internal notes or the real quote."""

    indicative_total = MoneyField()
    package_name = serializers.CharField(source="package.name", read_only=True, default="")
    respond_by = serializers.DateTimeField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CateringEnquiry
        # Lists, not tuples: a subclass extending a fixed-length tuple is a
        # type error, and EnquiryCreatedSerializer adds a field.
        fields = [
            "reference",
            "status",
            "status_display",
            "name",
            "email",
            "phone",
            "guest_count",
            "package_name",
            "indicative_total",
            "event_type",
            "event_date",
            "event_time",
            "venue",
            "message",
            "respond_by",
            "created_at",
        ]
        read_only_fields = fields


class EnquiryCreatedSerializer(EnquirySerializer):
    """Adds the wording that replaces the frontend's unbacked promise."""

    indicative_note = serializers.SerializerMethodField()

    class Meta(EnquirySerializer.Meta):
        fields = [*EnquirySerializer.Meta.fields, "indicative_note"]

    def get_indicative_note(self, obj: CateringEnquiry) -> str:
        if not obj.indicative_total:
            return "We will price this for you once we know a little more."
        return "Indicative only — a member of our team will confirm your quote."
