"""Support endpoints."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsStaffMember, current_user
from apps.common.throttling import SCOPED_THROTTLES
from apps.core.selectors import get_current_branch
from apps.support.models import FaqEntry, Ticket
from apps.support.serializers import (
    ContactAckSerializer,
    ContactSerializer,
    CreateReplySerializer,
    FaqSerializer,
    OpenTicketsSerializer,
    TicketSerializer,
)
from apps.support.services import reply_to_ticket, submit_contact_message


class ContactView(APIView):
    """Submit the contact form.

    Unlike the current implementation, the message is stored, a ticket is
    opened, the customer is acknowledged and the team is emailed.
    """

    permission_classes = [AllowAny]
    throttle_scope = "contact"
    throttle_classes = SCOPED_THROTTLES

    @extend_schema(
        summary="Send a message",
        request=ContactSerializer,
        responses={201: ContactAckSerializer},
        tags=["support"],
    )
    def post(self, request: Request) -> Response:
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket = submit_contact_message(
            branch=get_current_branch(),
            name=data["name"],
            email=data["email"],
            phone=data.get("phone", ""),
            reason=data.get("reason"),
            subject=data.get("subject", ""),
            message=data["message"],
            user=request.user,
            honeypot=data.get("website", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("User-Agent", ""),
        )
        # A quarantined message gets the same response as a real one: telling a
        # bot it was caught only helps it try again.
        return Response(
            {
                "reference": ticket.reference if ticket else "",
                "detail": "Thanks — we have your message and will be in touch.",
            },
            status=status.HTTP_201_CREATED,
        )


class FaqListView(ListAPIView):
    """Published answers. Powers the help page."""

    permission_classes = [AllowAny]
    serializer_class = FaqSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        queryset = FaqEntry.objects.filter(is_active=True)
        category = self.request.query_params.get("category", "")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    @extend_schema(summary="List FAQ entries", tags=["support"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class MyTicketsView(ListAPIView):
    """The signed-in customer's tickets."""

    permission_classes = [IsAuthenticated]
    serializer_class = TicketSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Ticket.objects.filter(user=current_user(self.request)).prefetch_related("replies")

    @extend_schema(summary="My support tickets", tags=["support"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class TicketDetailView(APIView):
    """One ticket thread."""

    permission_classes = [AllowAny]

    def _get(self, request: Request, reference: str) -> Ticket | None:
        ticket = get_object_or_404(Ticket.objects.prefetch_related("replies"), reference=reference)
        user = request.user
        if user.is_authenticated:
            if ticket.user_id and ticket.user_id == user.pk:
                return ticket
            if user.is_staff or user.groups.filter(name__in=["managers", "kitchen"]).exists():
                return ticket
        supplied = request.query_params.get("email", "").strip().lower()
        if supplied and constant_time_compare(ticket.requester_email, supplied):
            return ticket
        return None

    @extend_schema(summary="Retrieve a ticket", responses={200: TicketSerializer}, tags=["support"])
    def get(self, request: Request, reference: str) -> Response:
        ticket = self._get(request, reference)
        if ticket is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(TicketSerializer(ticket).data)

    @extend_schema(
        summary="Reply to a ticket",
        request=CreateReplySerializer,
        responses={201: TicketSerializer},
        tags=["support"],
    )
    def post(self, request: Request, reference: str) -> Response:
        ticket = self._get(request, reference)
        if ticket is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = CreateReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        author = request.user if request.user.is_authenticated else None
        staff = bool(author and (author.is_staff or author.groups.exists()))
        reply_to_ticket(
            ticket=ticket,
            body=serializer.validated_data["body"],
            author=author if staff else None,
            internal=False,
        )
        ticket.refresh_from_db()
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class OpenTicketsView(APIView):
    """The support queue, for staff."""

    permission_classes = [IsStaffMember]

    @extend_schema(
        summary="Open support tickets",
        responses={200: OpenTicketsSerializer},
        tags=["support"],
    )
    def get(self, request: Request) -> Response:
        from apps.support.models import TicketStatus

        tickets = (
            Ticket.objects.filter(
                branch=get_current_branch(),
                status__in=[TicketStatus.OPEN, TicketStatus.PENDING],
            )
            .prefetch_related("replies")
            .order_by("created_at")
        )
        return Response(
            {"count": tickets.count(), "tickets": TicketSerializer(tickets, many=True).data}
        )
