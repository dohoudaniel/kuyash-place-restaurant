"""Session and CSRF endpoints."""

from __future__ import annotations

from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import SessionSerializer


class CSRFView(APIView):
    """Seeds the CSRF cookie.

    The frontend calls this once on app load, then echoes the cookie value in an
    ``X-CSRFToken`` header on every unsafe request.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Seed the CSRF cookie",
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        get_token(request)
        return Response({"detail": "CSRF cookie set."}, status=status.HTTP_200_OK)


class SessionView(APIView):
    """Returns the current user, or ``{"user": null}`` when anonymous."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Current session",
        responses={200: SessionSerializer},
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        user = request.user if request.user.is_authenticated else None
        return Response(SessionSerializer({"user": user}).data)
