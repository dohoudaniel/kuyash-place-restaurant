"""Chat assistant endpoints."""

from __future__ import annotations

from typing import Any

from django.http import Http404
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.views import CsrfEnforcedMixin
from apps.common.throttling import SCOPED_THROTTLES
from apps.core.selectors import get_current_branch
from apps.support import chat
from apps.support.models import ChatSession
from apps.support.serializers import (
    ChatEscalatedSerializer,
    ChatEscalateSerializer,
    ChatExchangeSerializer,
    ChatMessageSerializer,
    ChatSendSerializer,
    ChatSessionCreatedSerializer,
    ChatSessionSerializer,
)

CHAT_TOKEN_HEADER = "X-Chat-Token"  # noqa: S105 — a header name, not a secret

TOKEN_PARAMETER = OpenApiParameter(
    CHAT_TOKEN_HEADER,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "The token returned when the conversation started. Not needed by its signed-in owner."
    ),
)


def _signed_in(request: Request) -> Any:
    return request.user if request.user.is_authenticated else None


def get_session(request: Request, session_id: Any) -> ChatSession:
    """The conversation, for its token holder or its signed-in owner only."""
    session = (
        ChatSession.objects.select_related("branch", "escalated_to_ticket")
        .prefetch_related("messages")
        .filter(pk=session_id)
        .first()
    )
    if session is None:
        raise Http404
    user = _signed_in(request)
    if user is not None and session.user_id and session.user_id == user.pk:
        return session
    supplied = request.headers.get(CHAT_TOKEN_HEADER, "")
    if supplied and constant_time_compare(session.session_token, supplied):
        return session
    raise Http404


class ChatSessionCreateView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "chat_session"

    @extend_schema(
        summary="Start a conversation",
        request=None,
        responses={201: ChatSessionCreatedSerializer},
        tags=["support"],
    )
    def post(self, request: Request) -> Response:
        session = chat.start_session(branch=get_current_branch(), user=_signed_in(request))
        return Response(ChatSessionCreatedSerializer(session).data, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reopen a conversation",
        parameters=[TOKEN_PARAMETER],
        responses={200: ChatSessionSerializer},
        tags=["support"],
    )
    def get(self, request: Request, session_id: Any) -> Response:
        return Response(ChatSessionSerializer(get_session(request, session_id)).data)


class ChatMessageCreateView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "chat_message"

    @extend_schema(
        summary="Send a message and get the assistant's reply",
        description=(
            "The assistant answers only from FAQ entries, an order lookup and opening "
            "hours. 409 `chat_ended`, `chat_expired` or `chat_limit` mean: start a new "
            "conversation."
        ),
        parameters=[TOKEN_PARAMETER],
        request=ChatSendSerializer,
        responses={201: ChatExchangeSerializer},
        tags=["support"],
    )
    def post(self, request: Request, session_id: Any) -> Response:
        session = get_session(request, session_id)
        serializer = ChatSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message, reply = chat.post_message(
            session, serializer.validated_data["body"], user=_signed_in(request)
        )
        return Response(
            {
                "message": ChatMessageSerializer(message).data,
                "reply": ChatMessageSerializer(reply).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ChatEscalateView(CsrfEnforcedMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = SCOPED_THROTTLES
    throttle_scope = "chat_escalate"

    @extend_schema(
        summary="Hand the conversation to a person",
        description=(
            "Opens a support ticket with the transcript. Calling it again returns the same ticket."
        ),
        parameters=[TOKEN_PARAMETER],
        request=ChatEscalateSerializer,
        responses={201: ChatEscalatedSerializer},
        tags=["support"],
    )
    def post(self, request: Request, session_id: Any) -> Response:
        session = get_session(request, session_id)
        serializer = ChatEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = _signed_in(request)

        name = data["name"].strip() or (user.get_full_name() if user else "")
        email = data["email"].strip() or (user.email if user else "")
        if not session.escalated_to_ticket_id and not (name and email):
            from rest_framework.exceptions import ValidationError

            errors = {}
            if not name:
                errors["name"] = ["Tell us your name."]
            if not email:
                errors["email"] = ["Tell us where to reply."]
            raise ValidationError(errors)

        ticket, reply = chat.escalate(
            session, name=name, email=email, note=data["message"], user=user
        )
        # A quarantined conversation gets the same shape as a real one.
        return Response(
            {
                "reference": ticket.reference if ticket else "",
                "reply": ChatMessageSerializer(reply).data if reply else None,
            },
            status=status.HTTP_201_CREATED,
        )
