"""Catering endpoints."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catering.models import CateringEnquiry, CateringPackage
from apps.catering.serializers import (
    CateringPackageSerializer,
    CreateEnquirySerializer,
    EnquiryCreatedSerializer,
    EnquirySerializer,
    OverdueEnquiriesSerializer,
)
from apps.catering.services import submit_enquiry
from apps.common.permissions import IsManager
from apps.core.selectors import get_current_branch


class PackageListView(ListAPIView):
    """The catering tiers."""

    permission_classes = [AllowAny]
    serializer_class = CateringPackageSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return CateringPackage.objects.filter(branch=get_current_branch(), is_active=True)

    @extend_schema(summary="List catering packages", tags=["catering"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class EnquiryCreateView(APIView):
    """Submit a catering enquiry.

    Unlike the current form, this persists the enquiry, acknowledges the
    customer with a concrete response deadline, and puts it in front of a human.
    """

    permission_classes = [AllowAny]
    throttle_scope = "catering"

    @extend_schema(
        summary="Submit a catering enquiry",
        request=CreateEnquirySerializer,
        responses={201: EnquiryCreatedSerializer},
        tags=["catering"],
    )
    def post(self, request: Request) -> Response:
        serializer = CreateEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        branch = get_current_branch()
        package = None
        if data.get("package"):
            package = CateringPackage.objects.filter(
                branch=branch, slug=data["package"], is_active=True
            ).first()

        enquiry = submit_enquiry(
            branch=branch,
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            guest_count=data["guest_count"],
            package=package,
            event_type=data.get("event_type", ""),
            event_date=data.get("event_date"),
            event_time=data.get("event_time"),
            venue=data.get("venue", ""),
            message=data.get("message", ""),
            user=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(EnquiryCreatedSerializer(enquiry).data, status=status.HTTP_201_CREATED)


class EnquiryDetailView(APIView):
    """Check an enquiry's progress."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve a catering enquiry",
        responses={200: EnquirySerializer},
        tags=["catering"],
    )
    def get(self, request: Request, reference: str) -> Response:
        enquiry = get_object_or_404(
            CateringEnquiry.objects.select_related("package", "branch"), reference=reference
        )
        user = request.user
        allowed = bool(
            user.is_authenticated
            and (
                (enquiry.user_id and enquiry.user_id == user.pk)
                or user.is_staff
                or user.groups.filter(name="managers").exists()
            )
        )
        if not allowed:
            # Guests confirm ownership with the email address they used.
            supplied = request.query_params.get("email", "").strip().lower()
            allowed = bool(supplied) and constant_time_compare(enquiry.email, supplied)
        if not allowed:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(EnquirySerializer(enquiry).data)


class OverdueEnquiriesView(APIView):
    """Enquiries past the 24 hours the website promises.

    The list a manager should open every morning.
    """

    permission_classes = [IsManager]

    @extend_schema(
        summary="Overdue catering enquiries",
        responses={200: OverdueEnquiriesSerializer},
        tags=["catering"],
    )
    def get(self, request: Request) -> Response:
        from apps.catering.services import overdue_enquiries

        branch = get_current_branch()
        overdue = overdue_enquiries(branch)
        return Response(
            {
                "count": len(overdue),
                "enquiries": [
                    {
                        **EnquirySerializer(enquiry).data,
                        "hours_overdue": round(-enquiry.hours_remaining, 1),
                    }
                    for enquiry in overdue
                ],
            }
        )
