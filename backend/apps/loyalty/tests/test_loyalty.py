"""Kuyash Rewards: ledger, earning, reversal, rewards at checkout, birthdays, expiry.

Replaces a page where "Join Free Now" set `signedUp = true` in component state.
"""

from __future__ import annotations

import datetime as dt
import io

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.accounts.services import anonymise_user
from apps.carts.services.pricing import price_cart
from apps.loyalty import services
from apps.loyalty.models import (
    LedgerEntryType,
    LoyaltyAccount,
    LoyaltyTier,
    PointsLedgerEntry,
    Reward,
    RewardRedemption,
    RewardRedemptionStatus,
)
from apps.loyalty.seed import REWARDS, TIERS, seed_loyalty
from apps.orders.models import Order
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db

ACCOUNT = reverse("v1:loyalty:account")
LEDGER = reverse("v1:loyalty:ledger")
PROGRAMME = reverse("v1:loyalty:programme")
REWARDS_URL = reverse("v1:loyalty:rewards")
APPLIED = reverse("v1:loyalty:reward-applied")


def redeem_url(reward: Reward) -> str:
    return reverse("v1:loyalty:reward-redeem", kwargs={"reward_id": reward.pk})


@pytest.fixture
def tiers(db):  # type: ignore[no-untyped-def]
    seed = {t["name"]: LoyaltyTier.objects.create(**t) for t in TIERS}
    seed["Silver"].birthday_points = 100
    seed["Silver"].save()
    return seed


@pytest.fixture
def account(verified_user, tiers, branch) -> LoyaltyAccount:  # type: ignore[no-untyped-def]
    return services.get_account(verified_user)


def give(account: LoyaltyAccount, points: int) -> None:
    services.adjust(account=account, points=points, description="Test grant")
    account.refresh_from_db()


@pytest.fixture
def discount(branch) -> Reward:  # type: ignore[no-untyped-def]
    return Reward.objects.create(
        branch=branch, name="₦500 Off", points_cost=250, reward_type="discount", value=50_000
    )


def deliver(order: Order) -> Order:
    for status in ("paid", "confirmed", "preparing", "ready", "delivered"):
        transition(order, status)
    order.refresh_from_db()
    return order


# ──────────────────────────────────────────────────────────────────────────────
# Ledger and tiers (LOY-1, LOY-3)
# ──────────────────────────────────────────────────────────────────────────────


def test_new_members_start_in_the_lowest_tier(account, tiers) -> None:  # type: ignore[no-untyped-def]
    assert account.tier == tiers["Silver"]
    assert account.points_balance == 0


def test_members_without_tiers_have_none(verified_user) -> None:  # type: ignore[no-untyped-def]
    assert services.get_account(verified_user).tier is None


def test_the_balance_is_the_ledger(account) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    give(account, -50)
    assert account.points_balance == 250
    assert (
        sum(PointsLedgerEntry.objects.filter(account=account).values_list("points", flat=True))
        == 250
    )


def test_ledger_entries_cannot_be_edited(account) -> None:  # type: ignore[no-untyped-def]
    give(account, 10)
    entry = PointsLedgerEntry.objects.get()
    entry.points = 1_000_000
    with pytest.raises(ValidationError):
        entry.save()


def test_earning_moves_tiers_and_spending_does_not_demote(account, tiers) -> None:  # type: ignore[no-untyped-def]
    give(account, 600)
    assert account.tier == tiers["Gold"]
    services.post_entry(
        account=account, entry_type=LedgerEntryType.REDEEM, points=-500, description="Spent"
    )
    account.refresh_from_db()
    assert account.points_balance == 100
    assert account.lifetime_points == 600
    assert account.tier == tiers["Gold"]


def test_idempotency_keys_post_once(account) -> None:  # type: ignore[no-untyped-def]
    first = services.post_entry(
        account=account, entry_type="earn", points=5, description="x", idempotency_key="k"
    )
    again = services.post_entry(
        account=account, entry_type="earn", points=5, description="x", idempotency_key="k"
    )
    assert first is not None and again is None
    account.refresh_from_db()
    assert account.points_balance == 5


def test_a_concurrent_duplicate_is_swallowed(account, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    services.post_entry(
        account=account, entry_type="earn", points=5, description="x", idempotency_key="race"
    )
    real_filter = PointsLedgerEntry.objects.filter

    class NeverExists:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(
        PointsLedgerEntry.objects,
        "filter",
        lambda **kw: NeverExists() if "idempotency_key" in kw else real_filter(**kw),
    )
    assert (
        services.post_entry(
            account=account, entry_type="earn", points=5, description="x", idempotency_key="race"
        )
        is None
    )


def test_adjustments_need_points_and_a_reason(account) -> None:  # type: ignore[no-untyped-def]
    from apps.common.exceptions import DomainError

    for points, reason in ((0, "why"), (5, "  ")):
        with pytest.raises(DomainError):
            services.adjust(account=account, points=points, description=reason)


# ──────────────────────────────────────────────────────────────────────────────
# Earning on delivery, reversal on refund (LOY-2, LOY-5)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def order(ready_cart, tiers) -> Order:  # type: ignore[no-untyped-def]
    return place_order(cart=ready_cart, payment_method="card")  # 2 × ₦10,900


def test_points_are_earned_when_the_order_is_delivered(order, verified_user) -> None:  # type: ignore[no-untyped-def]
    transition(order, "paid")
    assert not PointsLedgerEntry.objects.exists()
    deliver_from_paid(order)
    account = LoyaltyAccount.objects.get(user=verified_user)
    assert account.points_balance == 218  # ₦21,800 at 1 point per ₦100
    assert PointsLedgerEntry.objects.get().description == f"Order {order.reference}"


def deliver_from_paid(order: Order) -> None:
    for status in ("confirmed", "preparing", "ready", "delivered"):
        transition(order, status)


def test_higher_tiers_earn_faster(order, verified_user, tiers) -> None:  # type: ignore[no-untyped-def]
    account = services.get_account(verified_user)
    give(account, 500)  # Gold: 1.5×
    deliver(order)
    account.refresh_from_db()
    assert account.points_balance == 500 + 327


def test_discounts_and_delivery_do_not_earn(order) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(discount_total=1_000_000, delivery_fee=500_000)
    order.refresh_from_db()
    account = services.get_account(order.user)
    assert services.points_for_order(order, account) == 118


def test_guests_and_closed_accounts_earn_nothing(order, verified_user) -> None:  # type: ignore[no-untyped-def]
    account = services.get_account(verified_user)
    account.is_closed = True
    account.save()
    assert services.earn_for_order(order) is None
    Order.objects.filter(pk=order.pk).update(user=None)
    order.refresh_from_db()
    assert services.earn_for_order(order) is None


def test_tiny_orders_earn_nothing(order) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(subtotal=9_999, discount_total=0)
    order.refresh_from_db()
    assert services.earn_for_order(order) is None


def test_a_refund_reverses_earned_points_once(order, verified_user) -> None:  # type: ignore[no-untyped-def]
    deliver(order)
    transition(order, "refunded")
    services.reverse_order(order)  # a second call changes nothing
    account = LoyaltyAccount.objects.get(user=verified_user)
    assert account.points_balance == 0
    assert account.lifetime_points == 0
    reversal = PointsLedgerEntry.objects.get(entry_type=LedgerEntryType.REVERSAL)
    assert reversal.reversal_of.entry_type == LedgerEntryType.EARN


# ──────────────────────────────────────────────────────────────────────────────
# Rewards at checkout (LOY-4)
# ──────────────────────────────────────────────────────────────────────────────


def test_a_reward_prices_into_the_cart(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    priced = price_cart(ready_cart)
    assert priced.promo_discount == 0
    assert priced.discount_total == 50_000
    assert priced.reward["applied"] is True
    assert priced.grand_total == price_without_reward(ready_cart) - 50_000


def price_without_reward(cart):  # type: ignore[no-untyped-def]
    reward = cart.loyalty_reward
    cart.loyalty_reward = None
    total = price_cart(cart).grand_total
    cart.loyalty_reward = reward
    return total


def test_applying_needs_enough_points(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 100)
    with pytest.raises(services.InsufficientPoints) as caught:
        services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    assert "150 more points" in str(caught.value.detail)


def test_unavailable_rewards_cannot_be_applied(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 1_000)
    discount.stock = 0
    discount.save()
    with pytest.raises(services.RewardUnavailable):
        services.apply_reward(cart=ready_cart, reward=discount, user=account.user)


@pytest.mark.parametrize(
    ("setup", "problem"),
    [
        ("spend", "more points"),
        ("min_order", "Spend at least"),
        ("inactive", "no longer available"),
        ("guest", "Sign in"),
    ],
)
def test_a_reward_that_stops_applying_says_why(
    ready_cart, account, discount, setup, problem
) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    if setup == "spend":
        give(account, -100)
    elif setup == "min_order":
        Reward.objects.filter(pk=discount.pk).update(min_order_value=10_000_000)
    elif setup == "inactive":
        Reward.objects.filter(pk=discount.pk).update(is_active=False)
    elif setup == "guest":
        ready_cart.user = None
    ready_cart.loyalty_reward.refresh_from_db()
    priced = price_cart(ready_cart)
    assert priced.reward["applied"] is False
    assert problem in priced.reward["problem"]
    assert priced.discount_total == 0


def test_a_discount_never_exceeds_what_is_left_after_a_promo(ready_cart, account, branch) -> None:  # type: ignore[no-untyped-def]
    big = Reward.objects.create(
        branch=branch, name="Huge", points_cost=1, reward_type="discount", value=99_000_000
    )
    give(account, 10)
    services.apply_reward(cart=ready_cart, reward=big, user=account.user)
    priced = price_cart(ready_cart)
    assert priced.discount_total == priced.subtotal


def test_free_dish_rewards(ready_cart, account, branch, category) -> None:  # type: ignore[no-untyped-def]
    from apps.catalog.models import MenuItem

    burger = MenuItem.objects.get(slug="classic-smash-burger")
    free = Reward.objects.create(
        branch=branch, name="Free Burger", points_cost=10, reward_type="free_item", menu_item=burger
    )
    give(account, 10)
    services.apply_reward(cart=ready_cart, reward=free, user=account.user)
    assert price_cart(ready_cart).reward["discount_amount"] == 1_090_000  # one burger, not two

    fries = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Fries",
        slug="fries",
        base_price=300_000,
        needs_repricing=False,
    )
    Reward.objects.filter(pk=free.pk).update(menu_item=fries)
    ready_cart.loyalty_reward.refresh_from_db()
    assert "Add Fries" in price_cart(ready_cart).reward["problem"]


def test_free_delivery_rewards(ready_cart, account, branch) -> None:  # type: ignore[no-untyped-def]
    branch.free_delivery_threshold = None
    branch.save()
    free = Reward.objects.create(
        branch=branch, name="Free Delivery", points_cost=10, reward_type="free_delivery"
    )
    give(account, 10)
    before = price_cart(ready_cart).delivery_fee
    services.apply_reward(cart=ready_cart, reward=free, user=account.user)
    priced = price_cart(ready_cart)
    assert before > 0
    assert priced.delivery_fee == 0
    assert priced.delivery_note == "Free delivery applied with Free Delivery."


def test_placing_the_order_spends_the_points(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    discount.stock = 5
    discount.save()
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    order = place_order(cart=ready_cart, payment_method="card")

    account.refresh_from_db()
    assert account.points_balance == 50
    redemption = RewardRedemption.objects.get()
    assert redemption.order == order
    assert redemption.discount_amount == 50_000
    assert order.discount_total == 50_000
    discount.refresh_from_db()
    assert discount.stock == 4


def test_an_order_that_expires_returns_the_points(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    discount.stock = 5
    discount.save()
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    order = place_order(cart=ready_cart, payment_method="card")
    transition(order, "expired")

    account.refresh_from_db()
    assert account.points_balance == 300
    assert account.lifetime_points == 300  # a returned reward is not new earning
    redemption = RewardRedemption.objects.get()
    assert redemption.status == RewardRedemptionStatus.REVERSED
    discount.refresh_from_db()
    assert discount.stock == 5


def test_points_cannot_be_spent_twice_at_once(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    order = place_order(cart=ready_cart, payment_method="card")
    give(account, -50)  # balance 0 now
    with pytest.raises(services.InsufficientPoints):
        services.spend_reward_for_order(cart=ready_cart, order=order, discount=1)


def test_the_last_one_in_stock(ready_cart, account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    services.apply_reward(cart=ready_cart, reward=discount, user=account.user)
    order = Order.objects.create(branch=ready_cart.branch, user=account.user, payment_method="card")
    Reward.objects.filter(pk=discount.pk).update(stock=0)
    ready_cart.loyalty_reward.refresh_from_db()
    with pytest.raises(services.RewardUnavailable):
        services.spend_reward_for_order(cart=ready_cart, order=order, discount=1)


def test_reward_validation(branch) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError):
        Reward(branch=branch, name="x", points_cost=1, reward_type="discount", value=0).clean()
    with pytest.raises(ValidationError):
        Reward(branch=branch, name="x", points_cost=1, reward_type="free_item").clean()
    Reward(branch=branch, name="x", points_cost=1, reward_type="free_delivery").clean()


# ──────────────────────────────────────────────────────────────────────────────
# Birthdays (LOY-6), expiry and erasure
# ──────────────────────────────────────────────────────────────────────────────


def with_birthday(user: User, day: dt.date) -> None:
    Profile.objects.update_or_create(user=user, defaults={"date_of_birth": day})


def test_birthday_bonus_once_a_year(account) -> None:  # type: ignore[no-untyped-def]
    with_birthday(account.user, dt.date(1990, 9, 14))
    assert services.grant_birthday_bonuses(today=dt.date(2026, 9, 14)) == 1
    assert services.grant_birthday_bonuses(today=dt.date(2026, 9, 14)) == 0
    assert services.grant_birthday_bonuses(today=dt.date(2026, 9, 15)) == 0
    account.refresh_from_db()
    assert account.points_balance == 100
    assert services.grant_birthday_bonuses(today=dt.date(2027, 9, 14)) == 1


def test_leap_day_birthdays_are_celebrated_on_the_28th(account) -> None:  # type: ignore[no-untyped-def]
    with_birthday(account.user, dt.date(2000, 2, 29))
    assert services.grant_birthday_bonuses(today=dt.date(2027, 2, 28)) == 1
    assert services.grant_birthday_bonuses(today=dt.date(2028, 2, 28)) == 0
    assert services.grant_birthday_bonuses(today=dt.date(2028, 2, 29)) == 1


def test_no_birthday_bonus_without_a_tier_bonus(account, tiers) -> None:  # type: ignore[no-untyped-def]
    LoyaltyTier.objects.update(birthday_points=0)
    with_birthday(account.user, dt.date(1990, 1, 1))
    assert services.grant_birthday_bonuses(today=dt.date(2026, 1, 1)) == 0


def test_the_birthday_task_uses_business_today(account, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from apps.loyalty import tasks

    monkeypatch.setattr(services, "business_today", lambda: dt.date(2026, 3, 3))
    with_birthday(account.user, dt.date(1990, 3, 3))
    assert tasks.birthday_bonuses() == 1


def test_inactive_balances_expire(account, settings) -> None:  # type: ignore[no-untyped-def]
    from apps.loyalty import tasks

    settings.LOYALTY_EXPIRY_INACTIVE_DAYS = 365
    services.post_entry(account=account, entry_type="earn", points=400, description="Old order")
    PointsLedgerEntry.objects.update(created_at=timezone.now() - dt.timedelta(days=400))
    assert tasks.expire_inactive_points() == 1
    account.refresh_from_db()
    assert account.points_balance == 0
    assert services.expire_inactive() == 0  # nothing left to expire


def test_recent_activity_keeps_points(account) -> None:  # type: ignore[no-untyped-def]
    services.post_entry(account=account, entry_type="earn", points=400, description="Recent order")
    assert services.expire_inactive() == 0


def test_erasure_closes_the_account(order, verified_user) -> None:  # type: ignore[no-untyped-def]
    deliver(order)
    anonymise_user(verified_user)
    account = LoyaltyAccount.objects.get(user=verified_user)
    assert account.is_closed
    assert account.points_balance == 0
    services.close_account(
        User.objects.create_user(email="never@example.com", password="x" * 16)
    )  # no account: no-op


def test_labels(account, discount) -> None:  # type: ignore[no-untyped-def]
    give(account, 5)
    assert str(account.tier) == "Silver"
    assert str(account).endswith("5 pts")
    assert str(discount) == "₦500 Off (250 pts)"
    assert str(PointsLedgerEntry.objects.get()) == "+5 Adjustment: Test grant"
    redemption = RewardRedemption(
        account=account, reward=discount, points_spent=250, discount_amount=50_000
    )
    assert str(redemption) == "₦500 Off — Spent on an order"


def test_business_today_is_a_date() -> None:
    assert isinstance(services.business_today(), dt.date)


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────


def test_programme_is_public(api_client, tiers) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(PROGRAMME).json()
    assert [tier["name"] for tier in body["tiers"]] == ["Silver", "Gold", "Platinum"]
    assert body["tiers"][1]["earn_rate"] == "1.5 points per ₦100"
    assert body["tiers"][0]["earn_rate"] == "1 point per ₦100"
    assert body["base_earn_rate"] == "1 point per ₦100"
    assert body["expiry_inactive_days"] == 365


def test_account_shows_progress_to_the_next_tier(api_client, account, tiers) -> None:  # type: ignore[no-untyped-def]
    give(account, 250)
    api_client.force_authenticate(account.user)
    body = api_client.get(ACCOUNT).json()
    assert body["points_balance"] == 250
    assert body["tier"]["name"] == "Silver"
    assert body["next_tier"] == {"name": "Gold", "min_points": 500, "points_to_go": 250}
    assert body["progress_percent"] == 50
    assert body["applied_reward"] is None
    assert body["birthday_on_file"] is False


def test_top_tier_is_complete(api_client, account) -> None:  # type: ignore[no-untyped-def]
    give(account, 5_000)
    api_client.force_authenticate(account.user)
    body = api_client.get(ACCOUNT).json()
    assert body["next_tier"] is None and body["progress_percent"] == 100


def test_account_without_tiers(api_client, verified_user, branch) -> None:  # type: ignore[no-untyped-def]
    LoyaltyTier.objects.create(name="Gold", min_points=500)
    api_client.force_authenticate(verified_user)
    body = api_client.get(ACCOUNT).json()
    assert body["tier"] is None
    assert body["earn_rate"] == "1 point per ₦100"
    assert body["progress_percent"] == 0


def test_account_needs_sign_in(api_client) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(ACCOUNT).status_code in {401, 403}


def test_ledger_is_private_and_newest_first(api_client, account) -> None:  # type: ignore[no-untyped-def]
    give(account, 10)
    give(account, 20)
    other = services.get_account(User.objects.create_user(email="o@example.com", password="x" * 16))
    give(other, 99)
    api_client.force_authenticate(account.user)
    rows = api_client.get(LEDGER).json()["results"]
    assert [row["points"] for row in rows] == [20, 10]
    assert rows[0]["order_reference"] is None


def test_catalogue_shows_affordability_only_to_members(
    api_client, account, discount, branch
) -> None:  # type: ignore[no-untyped-def]
    Reward.objects.create(
        branch=branch, name="Hidden", points_cost=1, reward_type="free_delivery", is_active=False
    )
    anon = api_client.get(REWARDS_URL).json()
    assert [row["name"] for row in anon] == ["₦500 Off"]
    assert anon[0]["affordable"] is None and anon[0]["value"]["display"] == "₦500.00"
    assert anon[0]["min_order_value"] is None and anon[0]["menu_item"] is None

    give(account, 100)
    api_client.force_authenticate(account.user)
    mine = api_client.get(REWARDS_URL).json()[0]
    assert mine["affordable"] is False and mine["points_short"] == 150


def test_redeem_and_remove_through_the_api(api_client, account, discount, ready_cart) -> None:  # type: ignore[no-untyped-def]
    give(account, 300)
    api_client.force_authenticate(account.user)
    cart = api_client.post(redeem_url(discount)).json()
    assert cart["loyalty_reward"]["name"] == "₦500 Off"
    assert cart["loyalty_reward"]["discount"]["display"] == "₦500.00"
    assert cart["promo_discount"]["amount"] == 0
    assert api_client.get(ACCOUNT).json()["applied_reward"]["name"] == "₦500 Off"

    cart = api_client.delete(APPLIED).json()
    assert cart["loyalty_reward"] is None


def test_redeem_errors_have_stable_codes(api_client, account, discount) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(account.user)
    response = api_client.post(redeem_url(discount))
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_points"


def test_admin(client, account, discount) -> None:  # type: ignore[no-untyped-def]
    client.force_login(User.objects.create_superuser(email="root@example.com", password="x" * 16))
    response = client.post(
        reverse("admin:loyalty_pointsledgerentry_add"),
        {"account": str(account.pk), "points": "40", "description": "Apology for a late order"},
    )
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.points_balance == 40
    entry = PointsLedgerEntry.objects.get()
    assert entry.entry_type == LedgerEntryType.ADJUSTMENT
    for name in (
        "loyaltyaccount",
        "reward",
        "loyaltytier",
        "rewardredemption",
        "pointsledgerentry",
    ):
        assert client.get(reverse(f"admin:loyalty_{name}_changelist")).status_code == 200
    assert (
        client.get(reverse("admin:loyalty_loyaltyaccount_change", args=[account.pk])).status_code
        == 200
    )
    assert client.get(reverse("admin:loyalty_reward_add")).context["adminform"].form.initial[
        "branch"
    ] == str(discount.branch.pk)


def test_seed(branch) -> None:  # type: ignore[no-untyped-def]
    out = io.StringIO()
    assert seed_loyalty(branch, stdout=out) == len(TIERS) + len(REWARDS)
    assert seed_loyalty(branch) == 0
    assert not Reward.objects.filter(is_active=True).exists()
    assert "inactive until reviewed" in out.getvalue()
