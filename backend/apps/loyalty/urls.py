"""Loyalty routes."""

from __future__ import annotations

from django.urls import path

from apps.loyalty.views import (
    AccountView,
    AppliedRewardView,
    LedgerView,
    ProgrammeView,
    RewardListView,
    RewardRedeemView,
)

app_name = "loyalty"

urlpatterns = [
    path("tiers/", ProgrammeView.as_view(), name="programme"),
    path("account/", AccountView.as_view(), name="account"),
    path("ledger/", LedgerView.as_view(), name="ledger"),
    path("rewards/", RewardListView.as_view(), name="rewards"),
    path("rewards/applied/", AppliedRewardView.as_view(), name="reward-applied"),
    path("rewards/<uuid:reward_id>/redeem/", RewardRedeemView.as_view(), name="reward-redeem"),
]
