"""Authentication, profile and address endpoints."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.models import Address
from apps.accounts.serializers import (
    AddressSerializer,
    CurrentUserSerializer,
    EmailOnlySerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SessionSerializer,
    VerifyEmailSerializer,
)
from apps.accounts.throttles import (
    LoginEmailThrottle,
    LoginIPThrottle,
    PasswordResetEmailThrottle,
    PasswordResetIPThrottle,
    RegisterThrottle,
    ResendVerificationThrottle,
)
from apps.common.exceptions import DomainError
from apps.common.permissions import current_user


class AuthFailed(DomainError):
    code = "authentication_failed"
    status_code = status.HTTP_401_UNAUTHORIZED
    title = "Could not sign you in"


class EmailNotVerified(DomainError):
    code = "email_not_verified"
    status_code = status.HTTP_403_FORBIDDEN
    title = "Confirm your email address first"


class InvalidToken(DomainError):
    code = "invalid_token"
    status_code = status.HTTP_400_BAD_REQUEST
    title = "That link is invalid or has expired"


_ERROR_MAP = {
    "email_not_verified": EmailNotVerified,
    "invalid_token": InvalidToken,
    "weak_password": InvalidToken,
}


def _raise(error: services.AuthError) -> None:
    """Translate a service error into its API problem document."""
    domain = _ERROR_MAP.get(error.code, AuthFailed)
    raise domain(error.detail)


class CSRFView(APIView):
    """Seeds the CSRF cookie.

    The frontend calls this once on load, then echoes the cookie value in an
    ``X-CSRFToken`` header on every unsafe request.
    """

    permission_classes = [AllowAny]

    @extend_schema(summary="Seed the CSRF cookie", tags=["auth"], responses={200: dict})
    def get(self, request: Request) -> Response:
        get_token(request)
        return Response({"detail": "CSRF cookie set."})


class SessionView(APIView):
    """Returns the current user, or ``{"user": null}`` when anonymous."""

    permission_classes = [AllowAny]

    @extend_schema(summary="Current session", responses={200: SessionSerializer}, tags=["auth"])
    def get(self, request: Request) -> Response:
        user = request.user if request.user.is_authenticated else None
        return Response(SessionSerializer({"user": user}).data)


class RegisterView(APIView):
    """Create an account and send a verification email."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    @extend_schema(
        summary="Register",
        request=RegisterSerializer,
        responses={201: CurrentUserSerializer},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = services.register_user(
            email=data["email"],
            password=data["password"],
            full_name=data["full_name"],
            phone=data["phone"],
            marketing_opt_in=data.get("marketing_opt_in", False),
        )
        return Response(
            {
                "user": CurrentUserSerializer(user).data,
                "email_verification_required": True,
                "detail": "Check your email to confirm your address.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Establish a session."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    @extend_schema(
        summary="Log in",
        request=LoginSerializer,
        responses={200: CurrentUserSerializer},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.authenticate_user(
                request,
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except services.AuthError as error:
            _raise(error)

        django_login(request, user)
        return Response({"user": CurrentUserSerializer(user).data})


class LogoutView(APIView):
    """Destroy the session."""

    permission_classes = [AllowAny]

    @extend_schema(summary="Log out", request=None, responses={204: None}, tags=["auth"])
    def post(self, request: Request) -> Response:
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(APIView):
    """Confirm an email address and sign the user in."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify email",
        request=VerifyEmailSerializer,
        responses={200: CurrentUserSerializer},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.verify_email(request, serializer.validated_data["key"])
        except services.AuthError as error:
            _raise(error)

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": CurrentUserSerializer(user).data})


class ResendVerificationView(APIView):
    """Re-send the verification email.

    Responds identically whether or not the account exists (AS-3).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ResendVerificationThrottle]

    @extend_schema(
        summary="Resend verification email",
        request=EmailOnlySerializer,
        responses={200: dict},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models import User

        user = User.objects.filter(
            email=serializer.validated_data["email"].lower().strip(), is_active=True
        ).first()
        if user is not None and not user.is_email_verified:
            services.send_verification_email(user)
        return Response({"detail": "If that account exists, a confirmation email is on its way."})


class PasswordResetView(APIView):
    """Start a password reset. Always reports success (AS-3)."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetIPThrottle, PasswordResetEmailThrottle]

    @extend_schema(
        summary="Request a password reset",
        request=EmailOnlySerializer,
        responses={200: dict},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If that account exists, a reset link is on its way. It expires in 1 hour."}
        )


class PasswordResetConfirmView(APIView):
    """Complete a password reset."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm a password reset",
        request=PasswordResetConfirmSerializer,
        responses={200: dict},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_password_reset(
                uid=serializer.validated_data["uid"],
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except services.AuthError as error:
            _raise(error)
        except Exception as exc:  # Django's password validators
            raise InvalidToken(str(exc)) from exc

        return Response({"detail": "Your password has been changed. Please sign in."})


class PasswordChangeView(APIView):
    """Change a password while signed in."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        request=PasswordChangeSerializer,
        responses={200: dict},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.change_password(
                user=current_user(request),
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except services.AuthError as error:
            _raise(error)
        except Exception as exc:
            raise InvalidToken(str(exc)) from exc

        # Keep this session signed in; other devices are unaffected here because
        # the user proved knowledge of the current password.
        update_session_auth_hash(request, current_user(request))
        return Response({"detail": "Your password has been changed."})


class MeView(APIView):
    """Read, update or erase the current user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Current profile", responses={200: ProfileSerializer}, tags=["accounts"])
    def get(self, request: Request) -> Response:
        return Response(ProfileSerializer(current_user(request)).data)

    @extend_schema(
        summary="Update profile",
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
        tags=["accounts"],
    )
    def patch(self, request: Request) -> Response:
        serializer = ProfileSerializer(current_user(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Erase account (NDPR)", request=None, responses={204: None}, tags=["accounts"]
    )
    @transaction.atomic
    def delete(self, request: Request) -> Response:
        user = current_user(request)
        services.anonymise_user(user)
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressListCreateView(ListCreateAPIView):
    """The customer's address book."""

    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Address.objects.filter(user=current_user(self.request)).select_related("zone")

    @extend_schema(summary="List addresses", tags=["accounts"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Add an address", tags=["accounts"])
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer: Any) -> None:
        user = current_user(self.request)
        is_first = not Address.objects.filter(user=user).exists()
        make_default = serializer.validated_data.get("is_default", False) or is_first
        if make_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        serializer.save(user=user, is_default=make_default)


class AddressDetailView(RetrieveUpdateDestroyAPIView):
    """One saved address."""

    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self) -> Any:
        # Scoped to the caller: user A can never reach user B's address.
        return Address.objects.filter(user=current_user(self.request)).select_related("zone")

    def perform_update(self, serializer: Any) -> None:
        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=current_user(self.request), is_default=True).exclude(
                pk=serializer.instance.pk
            ).update(is_default=False)
        serializer.save()

    def perform_destroy(self, instance: Address) -> None:
        was_default = instance.is_default
        user = instance.user
        instance.delete()
        if was_default:
            replacement = Address.objects.filter(user=user).first()
            if replacement is not None:
                replacement.is_default = True
                replacement.save(update_fields=["is_default", "updated_at"])


class AddressSetDefaultView(APIView):
    """Promote an address to the default."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Set default address",
        request=None,
        responses={200: AddressSerializer},
        tags=["accounts"],
    )
    def post(self, request: Request, pk: str) -> Response:
        from django.shortcuts import get_object_or_404

        user = current_user(request)
        address = get_object_or_404(Address, pk=pk, user=user)
        Address.objects.filter(user=user, is_default=True).exclude(pk=address.pk).update(
            is_default=False
        )
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
        return Response(AddressSerializer(address).data)
