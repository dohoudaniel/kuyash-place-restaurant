"""``manage.py verify_restore`` — a restored database is usable, not merely present."""

from __future__ import annotations

import datetime as dt
import io
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.services.placement import place_order
from apps.orders.services.state import transition

pytestmark = pytest.mark.django_db


def run(*args: str) -> tuple[dict, str | None]:  # type: ignore[type-arg]
    out = io.StringIO()
    try:
        call_command("verify_restore", "--json", *args, stdout=out)
        error = None
    except CommandError as exc:
        error = str(exc)
    return json.loads(out.getvalue()), error


def check(report: dict, name: str) -> dict:  # type: ignore[type-arg]
    return next(c for c in report["checks"] if c["name"] == name)


@pytest.fixture
def paid_order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    from apps.payments.models import PaymentTransaction, Provider, TransactionStatus

    order = place_order(cart=ready_cart, payment_method="card")
    PaymentTransaction.objects.create(
        order=order,
        provider=Provider.PAYSTACK,
        our_reference=f"{order.reference}-1",
        amount=order.grand_total,
        amount_verified=order.grand_total,
        status=TransactionStatus.SUCCESS,
    )
    transition(order, OrderStatus.PAID)
    return order


def test_a_healthy_database_passes(paid_order) -> None:  # type: ignore[no-untyped-def]
    report, error = run()
    assert error is None
    assert report["ok"] is True
    assert report["counts"]["orders"] == 1
    assert all(c["ok"] for c in report["checks"])


def test_an_empty_database_passes_without_a_freshness_limit(db) -> None:  # type: ignore[no-untyped-def]
    report, error = run()
    assert error is None and report["ok"]


def test_a_total_that_no_longer_adds_up_fails(paid_order) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=paid_order.pk).update(grand_total=paid_order.grand_total + 1)
    report, error = run()
    assert error and "order_totals" in error
    assert paid_order.reference in check(report, "order_totals")["examples"][0]


def test_vat_exclusive_orders_add_vat(paid_order) -> None:  # type: ignore[no-untyped-def]
    order = Order.objects.get(pk=paid_order.pk)
    Order.objects.filter(pk=order.pk).update(
        prices_included_vat=False, grand_total=order.grand_total + order.vat_total
    )
    assert check(run()[0], "order_totals")["ok"] is True


def test_missing_order_lines_fail(paid_order) -> None:  # type: ignore[no-untyped-def]
    OrderItem.objects.filter(order=paid_order).delete()
    OrderItem.objects.create(
        order=paid_order, name_snapshot="Half", unit_price=1, quantity=1, line_subtotal=1
    )
    report, error = run()
    assert error and "order_lines" in error


def test_a_paid_card_order_without_its_payment_fails(paid_order) -> None:  # type: ignore[no-untyped-def]
    paid_order.transactions.all().delete()
    report, error = run()
    assert error and "paid_orders" in error
    assert check(report, "paid_orders")["examples"] == [paid_order.reference]


def test_a_cash_order_needs_no_payment_record(ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.models import PaymentStatus

    order = place_order(cart=ready_cart, payment_method="cash")
    Order.objects.filter(pk=order.pk).update(payment_status=PaymentStatus.PAID)
    assert check(run()[0], "paid_orders")["ok"] is True


def test_a_loyalty_balance_that_differs_from_its_ledger_fails(verified_user) -> None:  # type: ignore[no-untyped-def]
    from apps.loyalty.models import LedgerEntryType, LoyaltyAccount, PointsLedgerEntry

    account = LoyaltyAccount.objects.create(user=verified_user, points_balance=100)
    PointsLedgerEntry.objects.create(
        account=account, entry_type=LedgerEntryType.values[0], points=100, description="Earned"
    )
    assert check(run()[0], "loyalty_balances")["ok"] is True

    LoyaltyAccount.objects.filter(pk=account.pk).update(points_balance=250)
    report, error = run()
    assert error and "loyalty_balances" in error


def test_unreadable_staff_secrets_warn_but_do_not_fail(verified_user, settings) -> None:  # type: ignore[no-untyped-def]
    from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

    TOTP.activate(verified_user, generate_totp_secret())
    assert check(run()[0], "staff_mfa_secrets")["ok"] is True

    settings.SECRET_KEY = "restored-with-a-different-key-entirely"
    report, error = run()
    mfa = check(report, "staff_mfa_secrets")
    assert mfa["ok"] is False and mfa["warning_only"] is True
    assert mfa["examples"] == [verified_user.email]
    assert error is None, "a key mismatch is reported, not treated as a broken restore"


def test_pending_migrations_fail(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from django.db.migrations.executor import MigrationExecutor

    class Fake:
        app_label = "orders"
        name = "9999_from_the_future"

    monkeypatch.setattr(
        MigrationExecutor, "migration_plan", lambda self, targets: [(Fake(), False)]
    )
    report, error = run()
    assert error and "migrations" in error
    assert check(report, "migrations")["examples"] == ["orders.9999_from_the_future"]


def test_a_stale_dump_fails_the_freshness_limit(paid_order, verified_user) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    assert check(run("--max-age-hours", "24")[0], "freshness")["ok"] is True

    old = timezone.now() - dt.timedelta(days=3)
    Order.objects.update(created_at=old)
    User.objects.update(date_joined=old)
    report, error = run("--max-age-hours", "24")
    assert error and "freshness" in error


def test_freshness_fails_on_an_empty_database(db) -> None:  # type: ignore[no-untyped-def]
    _report, error = run("--max-age-hours", "24")
    assert error and "freshness" in error


def test_the_human_report_lists_each_check(paid_order) -> None:  # type: ignore[no-untyped-def]
    out = io.StringIO()
    call_command("verify_restore", stdout=out)
    text = out.getvalue()
    assert "✓ order_totals" in text and "Restore verified." in text

    paid_order.transactions.all().delete()
    out = io.StringIO()
    with pytest.raises(CommandError):
        call_command("verify_restore", stdout=out)
    assert "✗ paid_orders" in out.getvalue()
    assert f"- {paid_order.reference}" in out.getvalue()
