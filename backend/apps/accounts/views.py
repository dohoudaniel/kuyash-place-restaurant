"""Authentication, profile and address endpoints."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.models import Address
from apps.accounts.serializers import (
    AddressSerializer,
    AuthUserResponseSerializer,
    CurrentUserSerializer,
    DetailResponseSerializer,
    EmailOnlySerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    ProfileSerializer,
    RegisterResponseSerializer,
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
    ResendVerificationIPThrottle,
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


class WeakPassword(DomainError):
    """A rejected password is not a dead link.

    ``invalid_token`` used to cover both, so the frontend had to regex the prose
    to tell "your reset link expired, request a new one" from "pick a stronger
    password" — in a codebase whose own contract is to branch on the code and
    never on the message.
    """

    code = "weak_password"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    title = "That password is not strong enough"


class AlreadyVerified(DomainError):
    """The second click on a verification link is a success story, not an error.

    Distinguishing it lets the frontend say "you're all set — sign in" instead
    of "that link is invalid", followed by an offer to resend an email the API
    has already decided not to send.
    """

    code = "already_verified"
    status_code = status.HTTP_409_CONFLICT
    title = "That email address is already confirmed"


_ERROR_MAP = {
    "email_not_verified": EmailNotVerified,
    "invalid_token": InvalidToken,
    "weak_password": WeakPassword,
    "already_verified": AlreadyVerified,
}


def _raise(error: services.AuthError) -> None:
    """Translate a service error into its API problem document."""
    domain = _ERROR_MAP.get(error.code, AuthFailed)
    raise domain(error.detail)


class CsrfEnforcedMixin:
    """Require a CSRF token even when nobody is signed in.

    DRF only checks CSRF for requests it has authenticated from a session, and
    marks every other view CSRF-exempt. That leaves the sign-in endpoints — the
    ones a signed-out visitor posts to — unprotected, and they also accept
    form-encoded bodies. A page on any other site could then post a login form
    and sign the visitor into an attacker's account (login CSRF), so every
    purchase and address they enter afterwards lands in that account.

    The frontend already sends ``X-CSRFToken`` on every unsafe request, so this
    costs it nothing.
    """

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            SessionAuthentication().enforce_csrf(request)
        super().initial(request, *args, **kwargs)  # type: ignore[misc]


class CSRFView(APIView):
    """Seeds the CSRF cookie.

    The frontend calls this once on load, then echoes the cookie value in an
    ``X-CSRFToken`` header on every unsafe request.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Seed the CSRF cookie", tags=["auth"], responses={200: DetailResponseSerializer}
    )
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


class RegisterView(CsrfEnforcedMixin, APIView):
    """Create an account and send a verification email."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    @extend_schema(
        summary="Register",
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
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


class LoginView(CsrfEnforcedMixin, APIView):
    """Establish a session."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    @extend_schema(
        summary="Log in",
        request=LoginSerializer,
        responses={200: AuthUserResponseSerializer},
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


class LogoutView(CsrfEnforcedMixin, APIView):
    """Destroy the session."""

    permission_classes = [AllowAny]

    @extend_schema(summary="Log out", request=None, responses={204: None}, tags=["auth"])
    def post(self, request: Request) -> Response:
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(CsrfEnforcedMixin, APIView):
    """Confirm an email address and sign the user in."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify email",
        request=VerifyEmailSerializer,
        responses={200: AuthUserResponseSerializer},
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


class ResendVerificationView(CsrfEnforcedMixin, APIView):
    """Re-send the verification email.

    Responds identically whether or not the account exists (AS-3).
    """

    permission_classes = [AllowAny]
    # Per IP *and* per address, as PasswordResetView does. The email-keyed class
    # alone let one host mail-bomb unlimited addresses, because declaring
    # throttle_classes replaces the global anon throttle.
    throttle_classes = [ResendVerificationIPThrottle, ResendVerificationThrottle]

    @extend_schema(
        summary="Resend verification email",
        request=EmailOnlySerializer,
        responses={200: DetailResponseSerializer},
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


class PasswordResetView(CsrfEnforcedMixin, APIView):
    """Start a password reset. Always reports success (AS-3)."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetIPThrottle, PasswordResetEmailThrottle]

    @extend_schema(
        summary="Request a password reset",
        request=EmailOnlySerializer,
        responses={200: DetailResponseSerializer},
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If that account exists, a reset link is on its way. It expires in 1 hour."}
        )


class PasswordResetConfirmView(CsrfEnforcedMixin, APIView):
    """Complete a password reset."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm a password reset",
        request=PasswordResetConfirmSerializer,
        responses={200: DetailResponseSerializer},
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
        except DjangoValidationError as exc:  # Django's password validators
            raise WeakPassword(" ".join(exc.messages)) from exc

        # Every session for this user has just been deleted — including this
        # request's own, if the visitor was signed in. Log the request out too,
        # or the session middleware tries to save a row that no longer exists
        # and turns a successful reset into an HTML 400.
        django_logout(request)
        return Response({"detail": "Your password has been changed. Please sign in."})


class PasswordChangeView(APIView):
    """Change a password while signed in."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        request=PasswordChangeSerializer,
        responses={200: DetailResponseSerializer},
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
        except DjangoValidationError as exc:  # Django's password validators
            raise WeakPassword(" ".join(exc.messages)) from exc

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


@extend_schema_view(
    get=extend_schema(summary="Retrieve an address", tags=["accounts"]),
    put=extend_schema(summary="Replace an address", tags=["accounts"]),
    patch=extend_schema(summary="Update an address", tags=["accounts"]),
    delete=extend_schema(summary="Delete an address", tags=["accounts"]),
)
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
