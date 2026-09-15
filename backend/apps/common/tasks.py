"""Operational watchers behind DEPLOYMENT.md §9.

The alert table there promised signals nothing produced. These tasks produce
them, through the channel that already reaches people: an ``ERROR`` log becomes
a Sentry event (the default logging integration), so "page" means
``logger.error`` with a stable ``alert_*`` message to route on, and "warn" means
``logger.warning``. Nothing here changes an order or a payment.

* ``ops.heartbeat`` — every minute; ``/health/`` reports the scheduler as stale
  when it stops, because a dead beat silently stops payment reconciliation.
* ``ops.watch`` — every 10 minutes: payments stuck unverified, orders stuck in
  the kitchen, Celery queue depth.
* ``ops.daily_report`` — once a day, emails managers the orders still stuck.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Max, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "ops:beat-heartbeat"


@shared_task(name="ops.heartbeat", ignore_result=True)
def heartbeat() -> None:
    cache.set(HEARTBEAT_KEY, timezone.now().isoformat(), 24 * 3600)


def scheduler_status() -> str:
    """``ok``, ``stale: …`` or ``not seen`` — for the health endpoint."""
    raw = cache.get(HEARTBEAT_KEY)
    if not raw:
        return "not seen"
    age = (timezone.now() - dt.datetime.fromisoformat(raw)).total_seconds()
    if age > settings.OPS_BEAT_STALE_SECONDS:
        return f"stale: last run {int(age)}s ago"
    return "ok"


# ── Signals ───────────────────────────────────────────────────────────────────


def stale_payments() -> list[str]:
    """Payments still unverified well after reconciliation should have settled them.

    ``payments.verify_pending`` looks at anything older than five minutes every ten
    minutes, so a transaction pending for 30 means reconciliation is failing.
    """
    from apps.payments.models import PaymentTransaction, TransactionStatus

    now = timezone.now()
    return list(
        PaymentTransaction.objects.filter(
            status__in=[TransactionStatus.INITIALISED, TransactionStatus.PENDING],
            initialised_at__lt=now - dt.timedelta(minutes=30),
            initialised_at__gt=now - dt.timedelta(hours=24),
        ).values_list("our_reference", flat=True)
    )


def stuck_orders() -> list[dict[str, Any]]:
    """Orders sitting in ``confirmed`` or ``preparing`` longer than the threshold."""
    from apps.orders.models import Order, OrderStatus

    cutoff = timezone.now() - dt.timedelta(minutes=settings.OPS_STUCK_ORDER_MINUTES)
    rows = (
        Order.objects.filter(status__in=[OrderStatus.CONFIRMED, OrderStatus.PREPARING])
        .annotate(since=Max("events__created_at", filter=Q(events__to_status=F("status"))))
        .filter(since__lt=cutoff)
        .order_by("since")
        .values("reference", "status", "since")
    )
    return [
        {
            "reference": row["reference"],
            "status": row["status"],
            "minutes": int((timezone.now() - row["since"]).total_seconds() // 60),
        }
        for row in rows
    ]


def queue_depth() -> int | None:
    """Messages waiting on the default Celery queue, when the broker is Redis."""
    url = settings.CELERY_BROKER_URL
    if settings.CELERY_TASK_ALWAYS_EAGER or not url.startswith(("redis://", "rediss://")):
        return None
    try:
        import redis

        depth: Any = redis.Redis.from_url(url, socket_timeout=2).llen("celery")
        return int(depth)
    except Exception:
        logger.warning("ops_queue_depth_unavailable", exc_info=True)
        return None


@shared_task(name="ops.watch")
def watch() -> dict[str, Any]:
    payments = stale_payments()
    if len(payments) > settings.OPS_STALE_PAYMENT_ALERT:
        logger.error(
            "alert_stale_payments",
            extra={"count": len(payments), "references": payments[:10]},
        )

    orders = stuck_orders()
    if orders:
        logger.error(
            "alert_orders_stuck",
            extra={"count": len(orders), "orders": [o["reference"] for o in orders[:10]]},
        )

    depth = queue_depth()
    if depth is not None and depth > settings.OPS_QUEUE_DEPTH_WARN:
        logger.warning("alert_queue_depth", extra={"depth": depth})

    return {"stale_payments": len(payments), "stuck_orders": len(orders), "queue_depth": depth}


def report_recipients() -> list[str]:
    from apps.accounts.models import User
    from apps.common.permissions import GROUP_MANAGERS

    managers = User.objects.filter(is_active=True, groups__name=GROUP_MANAGERS).exclude(email="")
    emails = {*settings.OPS_ALERT_EMAILS, *managers.values_list("email", flat=True)}
    return sorted(email for email in emails if email)


@shared_task(name="ops.daily_report")
def daily_report() -> int:
    """Email managers the orders still stuck in the kitchen. Silent when there are none."""
    from apps.notifications.services import queue_email

    orders = stuck_orders()
    if not orders:
        return 0
    lines = [f"- {o['reference']}: {o['status']} for {o['minutes']} min" for o in orders]
    body = (
        f"{len(orders)} order(s) have been in the kitchen for more than "
        f"{settings.OPS_STUCK_ORDER_MINUTES} minutes:\n\n" + "\n".join(lines) + "\n\n"
        "Check the kitchen display: advance them, or cancel and refund.\n"
    )
    recipients = report_recipients()
    for recipient in recipients:
        queue_email(
            template_key="ops_stuck_orders",
            recipient=recipient,
            subject=f"Kuyash Place: {len(orders)} order(s) stuck in the kitchen",
            body=body,
        )
    return len(recipients)
