"""Order and Kitchen Display endpoints."""

from __future__ import annotations

import hashlib
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.services import cart as cart_services
from apps.carts.views import CART_TOKEN_HEADER
from apps.common import idempotency
from apps.common.exceptions import DomainError, IllegalTransition
from apps.common.pagination import CursorPagination
from apps.common.permissions import IsKitchenStaff, current_user
from apps.common.throttling import SCOPED_THROTTLES
from apps.core.selectors import get_current_branch
from apps.orders.models import EventSource, Order, OrderStatus
from apps.orders.serializers import (
    CancelSerializer,
    ItemAvailabilitySerializer,
    KDSQueueSerializer,
    KDSSummarySerializer,
    KDSTicketSerializer,
    OrderDetailResponseSerializer,
    OrderListSerializer,
    PlaceOrderSerializer,
    RiderAssignmentSerializer,
    kds_ticket,
    serialise_order,
)
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

GUEST_TOKEN_HEADER = "X-Guest-Token"  # noqa: S105 - a header name, not a credential


class MissingIdempotencyKey(DomainError):
    code = "idempotency_key_required"
    title = "An Idempotency-Key header is required"
    status_code = status.HTTP_400_BAD_REQUEST


def _order_etag(order: Order) -> str:
    """Weak ETag derived from the latest status event.

    Lets a polling client send ``If-None-Match`` and get a 304 with no body
    while nothing has happened.
    """
    latest = order.events.order_by("-created_at", "-id").first()
    seed = f"{order.reference}:{order.status}:{latest.pk if latest else 0}"
    return f'W/"{hashlib.sha256(seed.encode()).hexdigest()[:32]}"'


def _may_read(request: Request, order: Order) -> bool:
    user = request.user
    if user.is_authenticated:
        if order.user_id and order.user_id == user.pk:
            return True
        if user.is_staff or user.groups.filter(name__in=["managers", "kitchen", "riders"]).exists():
            return True
    supplied = request.headers.get(GUEST_TOKEN_HEADER, "")
    return (
        bool(order.guest_token)
        and bool(supplied)
        and constant_time_compare(order.guest_token, supplied)
    )


class OrderCreateListView(APIView):
    """Place an order, or list the caller's own."""

    permission_classes = [AllowAny]
    throttle_scope = "order_create"
    throttle_classes = SCOPED_THROTTLES

    @extend_schema(
        summary="Place an order",
        request=PlaceOrderSerializer,
        responses={201: OrderDetailResponseSerializer},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                str,
                OpenApiParameter.HEADER,
                required=True,
                description="A UUID. Replaying it returns the original response.",
            )
        ],
        tags=["orders"],
    )
    def post(self, request: Request) -> Response:
        key = request.headers.get(idempotency.HEADER, "").strip()
        if not key:
            raise MissingIdempotencyKey(
                "Send an Idempotency-Key header so a repeated submission cannot "
                "place a second order."
            )

        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cache_key, replayed = idempotency.begin("orders", key, request.data)
        if replayed is not None:
            response = Response(replayed, status=status.HTTP_201_CREATED)
            response["Idempotency-Replayed"] = "true"
            return response

        try:
            cart = cart_services.resolve_cart(
                branch=get_current_branch(),
                user=request.user if request.user.is_authenticated else None,
                session_token=request.headers.get(CART_TOKEN_HEADER, ""),
            )
            order = place_order(
                cart=cart,
                payment_method=data["payment_method"],
                expected_total=data.get("expected_total"),
                guest=data.get("guest") or {},
                customer_note=data.get("customer_note", ""),
                idempotency_key=key,
            )
        except Exception:
            # Release the claim so the customer can correct and retry.
            idempotency.abandon(cache_key)
            raise

        body = serialise_order(order, include_token=order.user_id is None)
        idempotency.complete(cache_key, body)
        return Response(body, status=status.HTTP_201_CREATED)


class OrderHistoryView(ListAPIView):
    """The caller's order history."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    pagination_class = CursorPagination

    def get_queryset(self) -> Any:
        return Order.objects.filter(user=current_user(self.request)).prefetch_related("items")

    @extend_schema(summary="List my orders", tags=["orders"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class OrderDetailView(APIView):
    """One order. The polling target."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve an order",
        responses={200: OrderDetailResponseSerializer},
        parameters=[
            OpenApiParameter(
                GUEST_TOKEN_HEADER,
                str,
                OpenApiParameter.HEADER,
                description="Required for guest orders.",
            ),
            OpenApiParameter(
                "If-None-Match",
                str,
                OpenApiParameter.HEADER,
                description="Send the previous ETag to receive 304 when unchanged.",
            ),
        ],
        tags=["orders"],
    )
    def get(self, request: Request, reference: str) -> Response:
        order = get_object_or_404(
            Order.objects.prefetch_related("items__modifiers", "items__reviews", "events"),
            reference=reference,
        )
        if not _may_read(request, order):
            # 404 rather than 403: existence itself is not disclosed.
            return Response(status=status.HTTP_404_NOT_FOUND)

        etag = _order_etag(order)
        if request.headers.get("If-None-Match") == etag:
            return Response(status=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

        response = Response(serialise_order(order))
        response["ETag"] = etag
        return response


class OrderCancelView(APIView):
    """Customer-initiated cancellation."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Cancel an order",
        request=CancelSerializer,
        responses={200: OrderDetailResponseSerializer},
        tags=["orders"],
    )
    def post(self, request: Request, reference: str) -> Response:
        order = get_object_or_404(Order, reference=reference)
        if not _may_read(request, order):
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The state table permits staff to cancel a preparing order; a customer
        # may not (ORD-10). The endpoint enforces the narrower window, because
        # the transition table alone cannot distinguish who is asking.
        if not order.can_cancel:
            raise IllegalTransition(
                "This order is already being prepared and can no longer be cancelled "
                "online. Please call the restaurant."
            )

        transition(
            order,
            OrderStatus.CANCELLED,
            actor=None,
            source=EventSource.CUSTOMER,
            note=serializer.validated_data.get("reason") or "Cancelled by the customer.",
        )
        order.refresh_from_db()
        return Response(serialise_order(order))


# ──────────────────────────────────────────────────────────────────────────────
# Kitchen Display System
# ──────────────────────────────────────────────────────────────────────────────


class KDSQueueView(APIView):
    """The live ticket queue, oldest first."""

    permission_classes = [IsKitchenStaff]

    @extend_schema(
        summary="Kitchen queue",
        responses={200: KDSQueueSerializer},
        parameters=[OpenApiParameter("status", str, description="Comma-separated statuses.")],
        tags=["kds"],
    )
    def get(self, request: Request) -> Response:
        wanted = request.query_params.get(
            "status", "paid,confirmed,preparing,ready,out_for_delivery"
        )
        statuses = [value for value in wanted.split(",") if value]
        orders = (
            Order.objects.filter(branch=get_current_branch(), status__in=statuses)
            .prefetch_related("items__modifiers")
            .order_by("placed_at", "created_at")
        )
        return Response({"orders": [kds_ticket(order) for order in orders]})


class KDSTransitionView(APIView):
    """Accept, reject or advance a ticket."""

    permission_classes = [IsKitchenStaff]

    ACTIONS = {
        "accept": OrderStatus.CONFIRMED,
        "reject": OrderStatus.REJECTED,
    }

    @extend_schema(
        summary="Advance a ticket", request=None, responses={200: KDSTicketSerializer}, tags=["kds"]
    )
    def post(self, request: Request, reference: str, action: str) -> Response:
        order = get_object_or_404(Order, reference=reference, branch=get_current_branch())

        if action == "advance":
            target = request.data.get("to", "")
            allowed = {
                OrderStatus.PREPARING,
                OrderStatus.READY,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED,
            }
            if target not in allowed:
                raise DomainError(f"“{target}” is not a status a ticket can be advanced to.")
        else:
            target = self.ACTIONS.get(action, "")
            if not target:
                raise DomainError(f"Unknown action “{action}”.")

        transition(
            order,
            target,
            actor=request.user,
            source=EventSource.STAFF,
            note=request.data.get("note", ""),
        )
        order.refresh_from_db()
        return Response(kds_ticket(order))


class KDSAvailabilityView(APIView):
    """ "86" an item — make it unavailable immediately."""

    permission_classes = [IsKitchenStaff]

    @extend_schema(
        summary="Set item availability",
        request=None,
        responses={200: ItemAvailabilitySerializer},
        tags=["kds"],
    )
    def post(self, request: Request, slug: str) -> Response:
        from apps.catalog.models import MenuItem

        item = get_object_or_404(MenuItem, slug=slug, branch=get_current_branch())
        item.is_available_now = bool(request.data.get("is_available_now", False))
        item.save(update_fields=["is_available_now", "updated_at"])
        return Response({"slug": item.slug, "is_available_now": item.is_available_now})


class KDSAssignRiderView(APIView):
    """Assign a rider to a ready order."""

    permission_classes = [IsKitchenStaff]

    @extend_schema(
        summary="Assign a rider",
        request=None,
        responses={200: RiderAssignmentSerializer},
        tags=["kds"],
    )
    def post(self, request: Request, reference: str) -> Response:
        from apps.delivery.models import DeliveryAssignment, RiderProfile

        order = get_object_or_404(Order, reference=reference, branch=get_current_branch())
        rider = get_object_or_404(RiderProfile, pk=request.data.get("rider"))

        assignment, _ = DeliveryAssignment.objects.update_or_create(
            order=order, defaults={"rider": rider}
        )
        return Response(
            {
                "order": order.reference,
                "rider": {"id": str(rider.pk), "name": rider.user.get_short_name()},
                "assigned_at": assignment.assigned_at.isoformat(),
            }
        )


class KDSSummaryView(APIView):
    """Counts and today's revenue."""

    permission_classes = [IsKitchenStaff]

    @extend_schema(summary="Kitchen summary", responses={200: KDSSummarySerializer}, tags=["kds"])
    def get(self, request: Request) -> Response:
        from django.db.models import Count

        from apps.carts.serializers import money

        branch = get_current_branch()
        counts = dict(
            Order.objects.filter(branch=branch).values_list("status").annotate(total=Count("id"))
        )
        # The same definition as the sales report, on the restaurant's own day.
        # This used to sum orders by UTC date, counting unpaid cash orders still
        # in the kitchen and missing confirmed and out-for-delivery ones.
        from apps.reporting import services as reports

        today = branch.local_now().date().isoformat()
        revenue = reports.sales(branch, reports.period(branch, start=today, end=today))["net"]
        return Response(
            {
                "counts": counts,
                "todays_revenue": money(revenue, branch.currency),
                "open_tickets": sum(
                    counts.get(value, 0)
                    for value in [OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]
                ),
            }
        )
