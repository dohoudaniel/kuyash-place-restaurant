"""Ledger postings, earning, reversals, rewards, birthdays and expiry."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Max, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import DomainError
from apps.common.money import format_money
from apps.loyalty.models import (
    LedgerEntryType,
    LoyaltyAccount,
    LoyaltyTier,
    PointsLedgerEntry,
    Reward,
    RewardRedemption,
    RewardRedemptionStatus,
    RewardType,
)

logger = logging.getLogger(__name__)

BASE_MULTIPLIER_BPS = 10_000


class InsufficientPoints(DomainError):
    code = "insufficient_points"
    title = "You don't have enough points for that reward"
    status_code = status.HTTP_409_CONFLICT


class RewardUnavailable(DomainError):
    code = "reward_unavailable"
    title = "That reward isn't available"
    status_code = status.HTTP_409_CONFLICT


# ──────────────────────────────────────────────────────────────────────────────
# The ledger
# ──────────────────────────────────────────────────────────────────────────────


def tier_for(lifetime_points: int) -> LoyaltyTier | None:
    return (
        LoyaltyTier.objects.filter(min_points__lte=max(lifetime_points, 0))
        .order_by("-min_points")
        .first()
    )


def next_tier(account: LoyaltyAccount) -> LoyaltyTier | None:
    return (
        LoyaltyTier.objects.filter(min_points__gt=max(account.lifetime_points, 0))
        .order_by("min_points")
        .first()
    )


def get_account(user: Any) -> LoyaltyAccount:
    account, created = LoyaltyAccount.objects.get_or_create(user=user)
    if created and account.tier is None:
        account.tier = tier_for(0)
        if account.tier is not None:
            account.save(update_fields=["tier", "updated_at"])
    return account


def _counts_toward_lifetime(entry_type: str, reversal_of: PointsLedgerEntry | None) -> bool:
    """Earning decides the tier. Spending points must not demote anyone."""
    if entry_type in {LedgerEntryType.EARN, LedgerEntryType.ADJUSTMENT}:
        return True
    return (
        entry_type == LedgerEntryType.REVERSAL
        and reversal_of is not None
        and reversal_of.entry_type == LedgerEntryType.EARN
    )


@transaction.atomic
def post_entry(
    *,
    account: LoyaltyAccount,
    entry_type: str,
    points: int,
    description: str,
    order: Any = None,
    reward: Reward | None = None,
    reversal_of: PointsLedgerEntry | None = None,
    created_by: Any = None,
    idempotency_key: str | None = None,
) -> PointsLedgerEntry | None:
    """Append one entry and move the cached balance and tier with it (LOY-1, LOY-3).

    Returns ``None`` when the idempotency key has already been posted.
    """
    if (
        idempotency_key
        and PointsLedgerEntry.objects.filter(idempotency_key=idempotency_key).exists()
    ):
        return None
    locked = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)
    try:
        with transaction.atomic():
            entry = PointsLedgerEntry.objects.create(
                account=locked,
                entry_type=entry_type,
                points=points,
                description=description[:200],
                order=order,
                reward=reward,
                reversal_of=reversal_of,
                created_by=created_by if getattr(created_by, "pk", None) else None,
                idempotency_key=idempotency_key,
            )
    except IntegrityError:  # the same event, posted concurrently
        return None

    locked.points_balance += points
    if _counts_toward_lifetime(entry_type, reversal_of):
        locked.lifetime_points += points
        locked.tier = tier_for(locked.lifetime_points)
    locked.save(update_fields=["points_balance", "lifetime_points", "tier", "updated_at"])
    account.points_balance = locked.points_balance
    account.lifetime_points = locked.lifetime_points
    account.tier = locked.tier
    return entry


def adjust(
    *, account: LoyaltyAccount, points: int, description: str, actor: Any = None
) -> PointsLedgerEntry:
    """A manual correction by staff, always with a reason."""
    if points == 0 or not description.strip():
        raise DomainError("An adjustment needs a non-zero number of points and a reason.")
    entry = post_entry(
        account=account,
        entry_type=LedgerEntryType.ADJUSTMENT,
        points=points,
        description=description.strip(),
        created_by=actor,
    )
    assert entry is not None  # no idempotency key, so it always posts
    return entry


# ──────────────────────────────────────────────────────────────────────────────
# Earning and reversal (LOY-2, LOY-5)
# ──────────────────────────────────────────────────────────────────────────────


def multiplier_label(bps: int) -> str:
    return f"{bps / BASE_MULTIPLIER_BPS:g}"


def earn_rate_label(bps: int = BASE_MULTIPLIER_BPS) -> str:
    """e.g. "1.5 points per ₦100"."""
    points = multiplier_label(bps)
    unit = format_money(settings.LOYALTY_KOBO_PER_POINT).removesuffix(".00")
    return f"{points} {'point' if points == '1' else 'points'} per {unit}"


def points_for_order(order: Any, account: LoyaltyAccount) -> int:
    """Points on what the customer paid for food: subtotal less discounts.

    Delivery, service charge and tips earn nothing.
    """
    spend = max(order.subtotal - order.discount_total, 0)
    base = spend // settings.LOYALTY_KOBO_PER_POINT
    bps = account.tier.points_multiplier_bps if account.tier else BASE_MULTIPLIER_BPS
    return base * bps // BASE_MULTIPLIER_BPS


def earn_for_order(order: Any) -> PointsLedgerEntry | None:
    user = order.user
    if user is None or not user.is_active:
        return None
    account = get_account(user)
    if account.is_closed:
        return None
    points = points_for_order(order, account)
    if points <= 0:
        return None
    return post_entry(
        account=account,
        entry_type=LedgerEntryType.EARN,
        points=points,
        description=f"Order {order.reference}",
        order=order,
        idempotency_key=f"earn:{order.reference}",
    )


@transaction.atomic
def reverse_order(order: Any) -> None:
    """An order that was refunded or never went through: undo its points (LOY-4, LOY-5)."""
    earned = PointsLedgerEntry.objects.filter(idempotency_key=f"earn:{order.reference}").first()
    if earned is not None:
        post_entry(
            account=earned.account,
            entry_type=LedgerEntryType.REVERSAL,
            points=-earned.points,
            description=f"Points from order {order.reference} reversed",
            order=order,
            reversal_of=earned,
            idempotency_key=f"reverse-earn:{order.reference}",
        )

    redemption = (
        RewardRedemption.objects.select_for_update()
        .select_related("reward", "account")
        .filter(order=order, status=RewardRedemptionStatus.SPENT)
        .first()
    )
    if redemption is None:
        return
    spent = PointsLedgerEntry.objects.filter(idempotency_key=f"redeem:{order.reference}").first()
    post_entry(
        account=redemption.account,
        entry_type=LedgerEntryType.REVERSAL,
        points=redemption.points_spent,
        description=f"{redemption.reward.name} returned — order {order.reference}",
        order=order,
        reward=redemption.reward,
        reversal_of=spent,
        idempotency_key=f"reverse-redeem:{order.reference}",
    )
    redemption.status = RewardRedemptionStatus.REVERSED
    redemption.reversed_at = timezone.now()
    redemption.save(update_fields=["status", "reversed_at", "updated_at"])
    if redemption.reward.stock is not None:
        Reward.objects.filter(pk=redemption.reward_id).update(stock=F("stock") + 1)


# ──────────────────────────────────────────────────────────────────────────────
# Rewards in the cart (LOY-4)
# ──────────────────────────────────────────────────────────────────────────────


def reward_is_available(reward: Reward) -> bool:
    if not reward.is_active or (reward.stock is not None and reward.stock <= 0):
        return False
    if reward.reward_type == RewardType.FREE_ITEM:
        return reward.menu_item is not None and reward.menu_item.is_active
    return True


def _balance(user: Any) -> int:
    account = LoyaltyAccount.objects.filter(user=user).first()
    return account.points_balance if account and not account.is_closed else 0


def apply_reward(*, cart: Any, reward: Reward, user: Any) -> Any:
    account = get_account(user)
    if account.is_closed or not reward_is_available(reward):
        raise RewardUnavailable("Choose another reward.")
    if account.points_balance < reward.points_cost:
        raise InsufficientPoints(
            f"You need {reward.points_cost - account.points_balance} more points for this reward."
        )
    cart.loyalty_reward = reward
    cart.save(update_fields=["loyalty_reward", "updated_at"])
    return cart


def remove_reward(*, cart: Any) -> Any:
    cart.loyalty_reward = None
    cart.save(update_fields=["loyalty_reward", "updated_at"])
    return cart


@dataclass(frozen=True, slots=True)
class RewardQuote:
    reward: Reward
    discount: int = 0
    free_delivery: bool = False
    problem: str = ""

    @property
    def applied(self) -> bool:
        return not self.problem

    def as_payload(self) -> dict[str, Any]:
        return {
            "id": str(self.reward.pk),
            "name": self.reward.name,
            "points_cost": self.reward.points_cost,
            "discount_amount": self.discount,
            "free_delivery": self.free_delivery,
            "applied": self.applied,
            "problem": self.problem,
        }


def quote_reward(
    cart: Any, *, subtotal: int, promo_discount: int, lines: list[tuple[Any, int]]
) -> RewardQuote:
    """What the applied reward is worth on this cart right now.

    Like a promo code, a reward whose conditions stop holding is not removed —
    it is shown with the reason it does not apply, and it takes nothing off.
    """
    reward = cart.loyalty_reward
    if cart.user is None:
        return RewardQuote(reward, problem="Sign in to use a reward.")
    if not reward_is_available(reward):
        return RewardQuote(reward, problem="This reward is no longer available.")
    balance = _balance(cart.user)
    if balance < reward.points_cost:
        return RewardQuote(
            reward, problem=f"You need {reward.points_cost - balance} more points for this reward."
        )
    if subtotal < reward.min_order_value:
        return RewardQuote(
            reward,
            problem=f"Spend at least {format_money(reward.min_order_value)} to use this reward.",
        )

    remaining = max(subtotal - promo_discount, 0)
    if reward.reward_type == RewardType.DISCOUNT:
        return RewardQuote(reward, discount=min(reward.value, remaining))
    if reward.reward_type == RewardType.FREE_ITEM:
        prices = [unit for menu_item, unit in lines if menu_item.pk == reward.menu_item_id]
        if not prices:
            return RewardQuote(
                reward, problem=f"Add {reward.menu_item.name} to your cart to use this reward."
            )
        return RewardQuote(reward, discount=min(min(prices), remaining))
    return RewardQuote(reward, free_delivery=True)


def spend_reward_for_order(*, cart: Any, order: Any, discount: int) -> RewardRedemption:
    """Spend the points as the order is placed, inside its transaction.

    Checked again under the account lock: two orders placed at once cannot both
    spend the same points.
    """
    reward = cart.loyalty_reward
    account = get_account(cart.user)
    locked = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)
    if locked.points_balance < reward.points_cost:
        raise InsufficientPoints("Your points balance changed. Remove the reward and try again.")
    if reward.stock is not None and not Reward.objects.filter(pk=reward.pk, stock__gt=0).update(
        stock=F("stock") - 1
    ):
        raise RewardUnavailable("That reward has just run out. Remove it and try again.")

    post_entry(
        account=locked,
        entry_type=LedgerEntryType.REDEEM,
        points=-reward.points_cost,
        description=f"{reward.name} — order {order.reference}",
        order=order,
        reward=reward,
        idempotency_key=f"redeem:{order.reference}",
    )
    return RewardRedemption.objects.create(
        account=locked,
        reward=reward,
        order=order,
        points_spent=reward.points_cost,
        discount_amount=discount,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Birthdays (LOY-6), expiry and closure
# ──────────────────────────────────────────────────────────────────────────────


def business_today() -> dt.date:
    from zoneinfo import ZoneInfo

    return timezone.localtime(timezone.now(), ZoneInfo(settings.BUSINESS_TIME_ZONE)).date()


def grant_birthday_bonuses(*, today: dt.date | None = None) -> int:
    """Once a year per member, on their birthday, at their tier's bonus.

    A 29 February birthday is celebrated on 28 February in other years.
    """
    import calendar

    from apps.accounts.models import Profile

    today = today or business_today()
    days = Q(date_of_birth__month=today.month, date_of_birth__day=today.day)
    if today.month == 2 and today.day == 28 and not calendar.isleap(today.year):
        days |= Q(date_of_birth__month=2, date_of_birth__day=29)

    granted = 0
    for profile in Profile.objects.filter(days, user__is_active=True).select_related("user"):
        account = get_account(profile.user)
        if account.is_closed or account.tier is None or not account.tier.birthday_points:
            continue
        entry = post_entry(
            account=account,
            entry_type=LedgerEntryType.EARN,
            points=account.tier.birthday_points,
            description="Happy birthday from Kuyash Place",
            idempotency_key=f"birthday:{profile.user_id}:{today.year}",
        )
        granted += int(entry is not None)
    return granted


#: How many accounts to look at per round trip. The scan is two queries per
#: batch regardless of size; this bounds how much is held in memory at once.
EXPIRY_BATCH_SIZE = 500


def expire_inactive(*, now: dt.datetime | None = None) -> int:
    """Expire balances untouched by an order or redemption for the configured period.

    The candidate scan is a single annotated aggregate per batch. It used to be
    one query per account to find each one's last activity: at 50,000 members
    that is 50,000 queries inside a task with a 240-second soft limit, so the
    task would be killed long before it reached the members whose points were
    actually due to expire — silently, every night.

    Batches are walked by primary key rather than by re-running the filter,
    because an account that is skipped (its expiry was already posted today)
    stays in the result set and would otherwise be looked at forever.
    """
    now = now or timezone.now()
    cutoff = now - dt.timedelta(days=settings.LOYALTY_EXPIRY_INACTIVE_DAYS)
    stamp = now.date().isoformat()

    candidates = (
        LoyaltyAccount.objects.filter(points_balance__gt=0, is_closed=False)
        .annotate(
            last_activity=Coalesce(
                Max(
                    "entries__created_at",
                    filter=Q(
                        entries__entry_type__in=[LedgerEntryType.EARN, LedgerEntryType.REDEEM]
                    ),
                ),
                "created_at",
            )
        )
        .filter(last_activity__lt=cutoff)
        .order_by("pk")
    )

    expired = 0
    after: Any = None
    while True:
        page = candidates.filter(pk__gt=after) if after is not None else candidates
        batch = list(page[:EXPIRY_BATCH_SIZE])
        if not batch:
            return expired

        # One query for the whole batch, rather than letting `post_entry` find
        # out one account at a time that there is nothing to do.
        keys = {account.pk: f"expire:{account.pk}:{stamp}" for account in batch}
        already = set(
            PointsLedgerEntry.objects.filter(idempotency_key__in=keys.values()).values_list(
                "idempotency_key", flat=True
            )
        )
        for account in batch:
            if keys[account.pk] in already:
                continue
            entry = post_entry(
                account=account,
                entry_type=LedgerEntryType.EXPIRE,
                points=-account.points_balance,
                description="Points expired after a period without activity",
                idempotency_key=keys[account.pk],
            )
            expired += int(entry is not None)
        after = batch[-1].pk


def close_account(user: Any) -> None:
    """On erasure: the balance goes, the ledger stays as the financial record."""
    account = LoyaltyAccount.objects.filter(user=user).first()
    if account is None:
        return
    if account.points_balance > 0:
        post_entry(
            account=account,
            entry_type=LedgerEntryType.EXPIRE,
            points=-account.points_balance,
            description="Account closed",
        )
    account.is_closed = True
    account.save(update_fields=["is_closed", "updated_at"])
