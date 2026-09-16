"""Core read-only endpoints.

Every one of these is public, identical for every visitor and changes a few
times a year, so they all carry a ``Cache-Control`` and the slower ones read
through the cache in ``apps/core/cache.py``. The frontend asks for
``/core/branch/`` on every page load; it used to cost about twenty queries.
"""

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

from apps.core.cache import (
    LEGAL_INDEX_KEY,
    LEGAL_PAGE_KEY,
    SITE_SETTINGS_KEY,
    TTL_MEDIUM,
    TTL_SHORT,
    PublicCacheMixin,
    cached,
)
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


class BranchView(PublicCacheMixin, APIView):
    """Branch details, VAT policy and whether ordering is currently possible."""

    permission_classes = [AllowAny]
    # Short: `is_open_now` flips at opening and closing time, and half a minute
    # of "we're still open" is the most this may ever be wrong by.
    cache_max_age = TTL_SHORT

    @extend_schema(summary="Branch details", responses={200: BranchSerializer}, tags=["core"])
    def get(self, request: Request) -> Response:
        return Response(BranchSerializer(get_current_branch()).data)


class OpeningHoursView(PublicCacheMixin, APIView):
    """The weekly schedule plus any upcoming holiday overrides."""

    permission_classes = [AllowAny]
    cache_max_age = TTL_MEDIUM

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


class SiteSettingsView(PublicCacheMixin, APIView):
    """Social links, homepage statistics and site copy."""

    permission_classes = [AllowAny]
    cache_max_age = TTL_MEDIUM

    @extend_schema(summary="Site settings", responses={200: SiteSettingsSerializer}, tags=["core"])
    def get(self, request: Request) -> Response:
        return Response(cached(SITE_SETTINGS_KEY, TTL_MEDIUM, _site_settings_payload))


def _site_settings_payload() -> dict[str, Any]:
    # `dict(...)` rather than DRF's ReturnDict: what goes into the cache must be
    # plain data, not something holding a reference to a serializer instance.
    return dict(SiteSettingsSerializer(SiteSettings.load()).data)


class LegalPageListView(PublicCacheMixin, APIView):
    """Which policy pages exist.

    Replaces a hardcoded array of footer links that could point at a page whose
    wording had since changed or been withdrawn.
    """

    permission_classes = [AllowAny]
    cache_max_age = TTL_MEDIUM

    @extend_schema(
        summary="Legal pages",
        responses={200: LegalPageSummarySerializer(many=True)},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        return Response(cached(LEGAL_INDEX_KEY, TTL_MEDIUM, _legal_index_payload))


def _legal_index_payload() -> list[dict[str, Any]]:
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
    current = [page for slug in slugs if (page := LegalPage.current(slug, on=today)) is not None]
    return [dict(row) for row in LegalPageSummarySerializer(current, many=True).data]


class LegalPageDetailView(PublicCacheMixin, APIView):
    """One policy page, at the version in force today.

    A future-dated version is a scheduled change and is not served; an
    unpublished one is a draft and is not served either.
    """

    permission_classes = [AllowAny]
    cache_max_age = TTL_MEDIUM

    @extend_schema(
        summary="A legal page",
        responses={200: LegalPageSerializer},
        tags=["core"],
    )
    def get(self, request: Request, slug: str) -> Response:
        # A missing page is never cached: "no such page" today may be "published
        # this afternoon" tomorrow, and a cached 404 on the terms page is worse
        # than a query.
        page = LegalPage.current(slug)
        if page is None:
            raise NotFound("No such page.")
        return Response(
            cached(
                LEGAL_PAGE_KEY.format(slug=slug),
                TTL_MEDIUM,
                lambda: dict(LegalPageSerializer(page).data),
            )
        )


class TeamListView(PublicCacheMixin, ListAPIView):
    """People on the About page. Empty until staff publish someone."""

    permission_classes = [AllowAny]
    serializer_class = TeamMemberSerializer
    pagination_class = None
    cache_max_age = TTL_MEDIUM

    def get_queryset(self) -> Any:
        return TeamMember.objects.filter(is_active=True)

    @extend_schema(summary="Team members", tags=["core"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class AwardListView(PublicCacheMixin, ListAPIView):
    """Verified awards. Empty until staff add one."""

    permission_classes = [AllowAny]
    serializer_class = AwardSerializer
    pagination_class = None
    cache_max_age = TTL_MEDIUM

    def get_queryset(self) -> Any:
        return Award.objects.filter(is_active=True)

    @extend_schema(summary="Awards and recognition", tags=["core"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)
