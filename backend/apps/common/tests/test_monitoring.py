"""Operational watchers (DEPLOYMENT.md §9) and the Sentry check command."""

from __future__ import annotations

import datetime as dt
import io
import logging
from typing import Any

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from apps.common import tasks
from apps.notifications.models import Notification
from apps.orders.models import OrderStatus, OrderStatusEvent
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


@pytest.fixture
def preparing_order(ready_cart):  # type: ignore[no-untyped-def]
    order = place_order(cart=ready_cart, payment_method="card")
    for status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
        transition(order, status)
    return order


def age_events(order: Any, minutes: int) -> None:
    OrderStatusEvent.objects.filter(order=order).update(
        created_at=timezone.now() - dt.timedelta(minutes=minutes)
    )


# ── Scheduler heartbeat ───────────────────────────────────────────────────────


def test_the_scheduler_is_not_seen_until_beat_runs(settings) -> None:  # type: ignore[no-untyped-def]
    assert tasks.scheduler_status() == "not seen"
    tasks.heartbeat()
    assert tasks.scheduler_status() == "ok"


def test_a_silent_scheduler_is_reported_stale(settings) -> None:  # type: ignore[no-untyped-def]
    settings.OPS_BEAT_STALE_SECONDS = 300
    old = timezone.now() - dt.timedelta(minutes=20)
    cache.set(tasks.HEARTBEAT_KEY, old.isoformat())
    assert tasks.scheduler_status().startswith("stale: last run 1200")


def test_health_reports_the_scheduler_with_a_broker(client, settings) -> None:  # type: ignore[no-untyped-def]
    settings.CELERY_TASK_ALWAYS_EAGER = False
    body = client.get(reverse("health-check")).json()
    assert body["checks"]["scheduler"] == "not seen"
    assert body["status"] == "ok", "a stale scheduler is reported, not a reason to restart web"

    tasks.heartbeat()
    assert client.get(reverse("health-check")).json()["checks"]["scheduler"] == "ok"


def test_health_omits_the_scheduler_when_eager(client) -> None:  # type: ignore[no-untyped-def]
    assert "scheduler" not in client.get(reverse("health-check")).json()["checks"]


# ── Watch ─────────────────────────────────────────────────────────────────────


def test_a_quiet_system_raises_nothing(preparing_order, caplog) -> None:  # type: ignore[no-untyped-def]
    with caplog.at_level(logging.WARNING, logger="apps.common.tasks"):
        result = tasks.watch()
    assert result == {"stale_payments": 0, "stuck_orders": 0, "queue_depth": None}
    assert not [r for r in caplog.records if r.getMessage().startswith("alert_")]


def test_an_order_stuck_in_the_kitchen_pages(preparing_order, settings, caplog) -> None:  # type: ignore[no-untyped-def]
    settings.OPS_STUCK_ORDER_MINUTES = 60
    age_events(preparing_order, 90)
    with caplog.at_level(logging.ERROR, logger="apps.common.tasks"):
        result = tasks.watch()
    assert result["stuck_orders"] == 1
    [record] = [r for r in caplog.records if r.getMessage() == "alert_orders_stuck"]
    assert record.levelno == logging.ERROR
    assert record.orders == [preparing_order.reference]  # type: ignore[attr-defined]


def test_time_counts_from_entering_the_current_status(preparing_order, settings) -> None:  # type: ignore[no-untyped-def]
    """An order placed long ago but only just moved to preparing is not stuck."""
    settings.OPS_STUCK_ORDER_MINUTES = 60
    OrderStatusEvent.objects.filter(order=preparing_order).exclude(
        to_status=OrderStatus.PREPARING
    ).update(created_at=timezone.now() - dt.timedelta(hours=5))
    assert tasks.stuck_orders() == []


def test_finished_orders_are_never_stuck(preparing_order, settings) -> None:  # type: ignore[no-untyped-def]
    transition(preparing_order, OrderStatus.READY)
    age_events(preparing_order, 500)
    assert tasks.stuck_orders() == []


def test_many_stale_payments_page(settings, caplog, ready_cart) -> None:  # type: ignore[no-untyped-def]
    settings.OPS_STALE_PAYMENT_ALERT = 1
    from apps.payments.models import PaymentTransaction, Provider, TransactionStatus

    order = place_order(cart=ready_cart, payment_method="card")

    def txn(reference: str, minutes: int, status: str = TransactionStatus.PENDING) -> None:
        PaymentTransaction.objects.create(
            order=order,
            provider=Provider.PAYSTACK,
            our_reference=reference,
            amount=1000,
            status=status,
            initialised_at=timezone.now() - dt.timedelta(minutes=minutes),
        )

    txn("KYS-OLD-1", 45)
    txn("KYS-OLD-2", 45)
    txn("KYS-FRESH", 10)  # reconciliation still has time
    txn("KYS-DONE", 45, TransactionStatus.SUCCESS)
    txn("KYS-ANCIENT", 60 * 30)  # outside the 24 h reconciliation window

    assert sorted(tasks.stale_payments()) == ["KYS-OLD-1", "KYS-OLD-2"]
    with caplog.at_level(logging.ERROR, logger="apps.common.tasks"):
        tasks.watch()
    assert any(r.getMessage() == "alert_stale_payments" for r in caplog.records)


def test_a_deep_queue_warns(settings, monkeypatch, caplog) -> None:  # type: ignore[no-untyped-def]
    settings.OPS_QUEUE_DEPTH_WARN = 100
    monkeypatch.setattr(tasks, "queue_depth", lambda: 250)
    with caplog.at_level(logging.WARNING, logger="apps.common.tasks"):
        assert tasks.watch()["queue_depth"] == 250
    [record] = [r for r in caplog.records if r.getMessage() == "alert_queue_depth"]
    assert record.levelno == logging.WARNING


def test_queue_depth_is_only_read_from_a_redis_broker(settings, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assert tasks.queue_depth() is None  # eager in tests

    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_BROKER_URL = "memory://localhost//"
    assert tasks.queue_depth() is None

    import redis

    class FakeRedis:
        def llen(self, name: str) -> int:
            assert name == "celery"
            return 7

    settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, url, **kw: FakeRedis()))
    assert tasks.queue_depth() == 7

    def broken(cls, url, **kw):  # type: ignore[no-untyped-def]
        raise ConnectionError("down")

    monkeypatch.setattr(redis.Redis, "from_url", classmethod(broken))
    assert tasks.queue_depth() is None


# ── Daily report ──────────────────────────────────────────────────────────────


def test_the_daily_report_emails_managers_and_listed_addresses(  # type: ignore[no-untyped-def]
    preparing_order, manager_user, settings
) -> None:
    settings.OPS_STUCK_ORDER_MINUTES = 60
    settings.OPS_ALERT_EMAILS = ["ops@example.com"]
    age_events(preparing_order, 75)

    assert tasks.daily_report() == 2
    sent = Notification.objects.filter(template_key="ops_stuck_orders")
    assert sorted(sent.values_list("recipient", flat=True)) == [
        "manager@kuyashplace.com",
        "ops@example.com",
    ]
    assert preparing_order.reference in sent.first().body  # type: ignore[union-attr]


def test_the_daily_report_is_silent_when_nothing_is_stuck(preparing_order, manager_user) -> None:  # type: ignore[no-untyped-def]
    assert tasks.daily_report() == 0
    assert not Notification.objects.filter(template_key="ops_stuck_orders").exists()


def test_every_watcher_is_scheduled() -> None:
    from django.conf import settings

    scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    assert {"ops.heartbeat", "ops.watch", "ops.daily_report"} <= scheduled


# ── Sentry check ──────────────────────────────────────────────────────────────


def test_sentry_check_refuses_without_a_dsn() -> None:
    with pytest.raises(CommandError, match="SENTRY_DSN"):
        call_command("sentry_check")


def test_sentry_check_sends_a_probe_that_gets_scrubbed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import sentry_sdk

    from apps.common.observability import scrub_event

    events: list[dict[str, Any]] = []

    class Transport(sentry_sdk.transport.Transport):
        def capture_envelope(self, envelope: Any) -> None:
            for item in envelope.items:
                if item.type == "event":
                    events.append(item.payload.json)

    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        transport=Transport,
        before_send=scrub_event,
        default_integrations=False,
    )
    try:
        out = io.StringIO()
        call_command("sentry_check", stdout=out)
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()  # back to an inactive client

    assert "Sent event" in out.getvalue()
    [event] = events
    probe = event["contexts"]["scrubbing_probe"]
    assert probe["ok"] == "visible"
    assert "must-not-arrive" not in str(event) and "4242424242424242" not in str(event)
