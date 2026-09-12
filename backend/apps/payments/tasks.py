"""Payment background tasks."""

from __future__ import annotations

import datetime as dt
import logging

from celery import shared_task
from django.utils import timezone

from apps.payments.models import PaymentTransaction, TransactionStatus

logger = logging.getLogger(__name__)


@shared_task(name="payments.verify_pending")
def verify_pending_payments() -> dict[str, int]:
    """Settle payments whose webhook never arrived.

    **Not optional.** Webhooks fail — the endpoint is down, DNS breaks, the
    provider has an incident — and money has already changed hands. This is the
    difference between "a customer paid and never got their food" and "the
    system healed itself within ten minutes".

    Runs every 10 minutes via beat.
    """
    from apps.payments.services.payments import PaymentAmountMismatch, verify_and_settle

    now = timezone.now()
    stale = PaymentTransaction.objects.filter(
        status__in=[TransactionStatus.INITIALISED, TransactionStatus.PENDING],
        initialised_at__lt=now - dt.timedelta(minutes=5),
        initialised_at__gt=now - dt.timedelta(hours=24),
    )

    counts = {"checked": 0, "settled": 0, "failed": 0}
    for record in stale.iterator():
        counts["checked"] += 1
        try:
            result = verify_and_settle(record, source="system")
        except PaymentAmountMismatch:
            counts["failed"] += 1
            continue
        except Exception:
            counts["failed"] += 1
            logger.exception("reconciliation_failed", extra={"transaction": str(record.pk)})
            continue
        if result.status == TransactionStatus.SUCCESS:
            counts["settled"] += 1

    if counts["settled"]:
        logger.info("reconciliation_settled", extra=counts)
    return counts


@shared_task(name="payments.expire_stale_orders")
def expire_stale_orders(minutes: int = 30) -> int:
    """Expire orders that never got paid, and give the customer their cart back."""
    from apps.orders.models import Order, OrderStatus
    from apps.orders.services.state import transition

    cutoff = timezone.now() - dt.timedelta(minutes=minutes)
    expired = 0
    for order in Order.objects.filter(
        status=OrderStatus.PENDING_PAYMENT, placed_at__lt=cutoff
    ).iterator():
        try:
            transition(order, OrderStatus.EXPIRED, source="system", note="Payment not completed.")
            expired += 1
        except Exception:
            logger.exception("expiry_failed", extra={"order": order.reference})
    return expired
