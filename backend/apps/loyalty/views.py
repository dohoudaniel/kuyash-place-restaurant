"""Loyalty endpoints."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.serializers import CartResponseSerializer
from apps.carts.views import CartBaseView
from apps.common.permissions import current_user
from apps.core.selectors import get_current_branch
from apps.loyalty import services
from apps.loyalty.models import PointsLedgerEntry, Reward
from apps.loyalty.serializers import (
    AccountSerializer,
    LedgerEntrySerializer,
    ProgrammeSerializer,
    RewardSerializer,
    programme_payload,
)


class ProgrammeView(APIView):
    """Tiers and earning rules. Public: the rewards page shows them to everyone."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Loyalty tiers and rules", responses={200: ProgrammeSerializer}, tags=["loyalty"]
    )
    def get(self, request: Request) -> Response:
        return Response(programme_payload())


class AccountView(CartBaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="My points, tier and progress", responses={200: AccountSerializer}, tags=["loyalty"]
    )
    def get(self, request: Request) -> Response:
        account = services.get_account(current_user(request))
        return Response(AccountSerializer(account, context={"cart": self.get_cart(request)}).data)


class LedgerView(ListAPIView):
    """Every points movement, newest first."""

    permission_classes = [IsAuthenticated]
    serializer_class = LedgerEntrySerializer

    def get_queryset(self) -> Any:
        return PointsLedgerEntry.objects.filter(
            account__user=current_user(self.request)
        ).select_related("order")

    @extend_schema(summary="My points history", tags=["loyalty"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class RewardListView(ListAPIView):
    """The catalogue. Signed-in members also see what they can afford."""

    permission_classes = [AllowAny]
    serializer_class = RewardSerializer
    pagination_class = None

    def get_queryset(self) -> Any:
        return Reward.objects.filter(branch=get_current_branch(), is_active=True).select_related(
            "menu_item"
        )

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            account = services.get_account(user)
            context["balance"] = 0 if account.is_closed else account.points_balance
        return context

    @extend_schema(summary="Rewards catalogue", tags=["loyalty"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class RewardRedeemView(CartBaseView):
    """Apply a reward to the cart. Points are spent when the order is placed."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Use a reward on my cart",
        description="409 `insufficient_points` or `reward_unavailable`.",
        request=None,
        responses={200: CartResponseSerializer},
        tags=["loyalty"],
    )
    def post(self, request: Request, reward_id: Any) -> Response:
        reward = get_object_or_404(
            Reward.objects.select_related("menu_item"),
            pk=reward_id,
            branch=get_current_branch(),
            is_active=True,
        )
        cart = self.get_cart(request)
        services.apply_reward(cart=cart, reward=reward, user=current_user(request))
        return self.render(cart)


class AppliedRewardView(CartBaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove the reward from my cart",
        responses={200: CartResponseSerializer},
        tags=["loyalty"],
    )
    def delete(self, request: Request) -> Response:
        cart = self.get_cart(request)
        services.remove_reward(cart=cart)
        return self.render(cart)
