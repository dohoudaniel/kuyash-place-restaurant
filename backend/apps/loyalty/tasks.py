"""Loyalty background tasks. Both are safe to run more than once a day."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="loyalty.birthday_bonuses")
def birthday_bonuses() -> int:
    from apps.loyalty.services import grant_birthday_bonuses

    return grant_birthday_bonuses()


@shared_task(name="loyalty.expire_inactive")
def expire_inactive_points() -> int:
    from apps.loyalty.services import expire_inactive

    return expire_inactive()
