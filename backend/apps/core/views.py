"""Core read-only endpoints."""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Award, LegalPage, SiteSettings, TeamMember
from apps.core.selectors import get_current_branch
from apps.core.serializers import (
    AwardSerializer,
    BranchSerializer,
    HolidayOverrideSerializer,
    LegalPageSerializer,
    LegalPageSummarySerializer,
    OpeningHoursResponseSerializer,
    OpeningHoursSerializer,
    SiteSettingsSerializer,
    TeamMemberSerializer,
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


class LegalPageListView(APIView):
    """Which policy pages exist.

    Replaces a hardcoded array of footer links that could point at a page whose
    wording had since changed or been withdrawn.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Legal pages",
        responses={200: LegalPageSummarySerializer(many=True)},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        today = timezone.localdate()
        # `.order_by()` first: the model's default ordering is (slug, -version),
        # and DISTINCT over an ordered queryset selects the ordering columns too,
        # so every version of a page would survive the dedupe as its own row.
        slugs = sorted(
            set(
                LegalPage.objects.filter(published=True, effective_from__lte=today)
                .order_by()
                .values_list("slug", flat=True)
            )
        )
        current = [
            page for slug in slugs if (page := LegalPage.current(slug, on=today)) is not None
        ]
        return Response(LegalPageSummarySerializer(current, many=True).data)


class LegalPageDetailView(APIView):
    """One policy page, at the version in force today.

    A future-dated version is a scheduled change and is not served; an
    unpublished one is a draft and is not served either.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="A legal page",
        responses={200: LegalPageSerializer},
        tags=["core"],
    )
    def get(self, request: Request, slug: str) -> Response:
        page = LegalPage.current(slug)
        if page is None:
            raise NotFound("No such page.")
        return Response(LegalPageSerializer(page).data)


class TeamListView(ListAPIView):
    """People on the About page. Empty until staff publish someone."""

    permission_classes = [AllowAny]
    serializer_class = TeamMemberSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return TeamMember.objects.filter(is_active=True)

    @extend_schema(summary="Team members", tags=["core"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class AwardListView(ListAPIView):
    """Verified awards. Empty until staff add one."""

    permission_classes = [AllowAny]
    serializer_class = AwardSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Award.objects.filter(is_active=True)

    @extend_schema(summary="Awards and recognition", tags=["core"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)
