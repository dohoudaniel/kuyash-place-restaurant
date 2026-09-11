"""Core read-only endpoints."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import SiteSettings
from apps.core.selectors import get_current_branch
from apps.core.serializers import (
    BranchSerializer,
    HolidayOverrideSerializer,
    OpeningHoursResponseSerializer,
    OpeningHoursSerializer,
    SiteSettingsSerializer,
)


class BranchView(APIView):
    """Branch details, VAT policy and whether ordering is currently possible."""

    permission_classes = [AllowAny]

    @extend_schema(summary="Branch details", responses={200: BranchSerializer}, tags=["core"])
    def get(self, request: Request) -> Response:
        return Response(BranchSerializer(get_current_branch()).data)


class OpeningHoursView(APIView):
    """The weekly schedule plus any upcoming holiday overrides."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Opening hours",
        responses={200: OpeningHoursResponseSerializer},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        branch = get_current_branch()
        return Response(
            {
                "is_open_now": branch.is_open_now,
                "timezone": branch.timezone,
                "hours": OpeningHoursSerializer(
                    branch.opening_hours.all().order_by("weekday", "opens_at"), many=True
                ).data,
                "overrides": HolidayOverrideSerializer(
                    branch.holiday_overrides.filter(date__gte=branch.local_now().date()),
                    many=True,
                ).data,
            }
        )


class SiteSettingsView(APIView):
    """Social links, homepage statistics and site copy."""

    permission_classes = [AllowAny]

    @extend_schema(summary="Site settings", responses={200: SiteSettingsSerializer}, tags=["core"])
    def get(self, request: Request) -> Response:
        return Response(SiteSettingsSerializer(SiteSettings.load()).data)
