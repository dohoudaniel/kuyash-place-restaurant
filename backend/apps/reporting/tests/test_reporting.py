"""Management reports: what counts as a sale, local days, items, peak hours, riders."""

from __future__ import annotations

import csv
import datetime as dt
import io
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.models import User
from apps.delivery.models import DeliveryAssignment, RiderProfile
from apps.orders.models import Order, OrderItem, OrderStatusEvent
from apps.payments.models import Refund
from apps.reporting import services

pytestmark = pytest.mark.django_db

LAGOS = ZoneInfo("Africa/Lagos")


def at(day: int, hour: int, minute: int = 0) -> dt.datetime:
    """A Lagos time in the week of Monday 7 September 2026."""
    return dt.datetime(2026, 9, day, hour, minute, tzinfo=LAGOS)


def order(
    branch,
    *,
    placed: dt.datetime,
    total: int = 1_000_000,
    method: str = "card",
    status: str = "delivered",
    payment: str = "paid",
    **extra,
) -> Order:  # type: ignore[no-untyped-def]
    return Order.objects.create(
        branch=branch,
        payment_method=method,
        status=status,
        payment_status=payment,
        placed_at=placed,
        subtotal=total,
        grand_total=total,
        **extra,
    )


def line(o: Order, name: str, quantity: int, unit: int, discount: int = 0) -> OrderItem:
    return OrderItem.objects.create(
        order=o,
        name_snapshot=name,
        slug_snapshot=name.lower(),
        unit_price=unit,
        quantity=quantity,
        line_subtotal=unit * quantity,
        line_discount=discount,
    )


@pytest.fixture
def week(branch):  # type: ignore[no-untyped-def]
    return services.period(branch, start="2026-09-07", end="2026-09-13")


@pytest.fixture
def manager(db):  # type: ignore[no-untyped-def]
    user = User.objects.create_user(
        email="mgr@example.com", password="x" * 16, full_name="Mo Manager", is_staff=True
    )
    user.groups.add(Group.objects.get_or_create(name="managers")[0])
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Periods
# ──────────────────────────────────────────────────────────────────────────────


def test_default_period_is_the_last_seven_local_days(branch) -> None:  # type: ignore[no-untyped-def]
    window = services.period(branch)
    assert window.days == 7
    assert window.end == branch.local_now().date()


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        ("2026-13-01", "", "YYYY-MM-DD"),
        ("2026-09-10", "2026-09-01", "on or before"),
        ("2024-01-01", "2026-01-01", "at most"),
    ],
)
def test_bad_periods_are_refused(branch, start, end, message) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(services.PeriodError, match=message):
        services.period(branch, start=start, end=end)


def test_days_are_lagos_days(branch, week) -> None:  # type: ignore[no-untyped-def]
    """00:30 on Monday in Lagos is 23:30 on Sunday in UTC; it still belongs to Monday."""
    order(branch, placed=at(7, 0, 30))
    order(branch, placed=at(6, 23, 30))  # Sunday before the week: outside
    order(branch, placed=at(14, 0, 10))  # Monday after: outside
    report = services.sales(branch, week)
    assert report["orders"] == 1
    assert report["daily"][0] == {"date": dt.date(2026, 9, 7), "orders": 1, "gross": 1_000_000}


# ──────────────────────────────────────────────────────────────────────────────
# Sales
# ──────────────────────────────────────────────────────────────────────────────


def test_what_counts_as_a_sale(branch, week) -> None:  # type: ignore[no-untyped-def]
    order(branch, placed=at(8, 12), total=2_000_000)  # paid card
    order(
        branch,
        placed=at(8, 13),
        total=1_500_000,
        method="cash",
        status="delivered",
        payment="unpaid",
    )  # delivered cash
    order(
        branch,
        placed=at(8, 14),
        total=3_000_000,
        method="cash",
        status="preparing",
        payment="unpaid",
    )  # cash not yet delivered
    order(branch, placed=at(8, 15), total=4_000_000, status="expired", payment="failed")
    order(
        branch, placed=at(8, 16), total=500_000, status="refunded", payment="refunded"
    )  # paid, then refunded
    report = services.sales(branch, week)
    assert report["orders"] == 3
    assert report["gross"] == 4_000_000
    assert report["average_order"] == 1_333_333
    assert report["by_payment_method"] == {
        "card": {"orders": 2, "gross": 2_500_000},
        "cash": {"orders": 1, "gross": 1_500_000},
    }
    assert report["incomplete_orders"]["expired"] == 1


def test_refunds_count_in_the_period_they_were_issued(branch, week) -> None:  # type: ignore[no-untyped-def]
    paid = order(branch, placed=at(1, 12), total=2_000_000)  # the week before
    refund = Refund.objects.create(order=paid, amount=500_000, status="success")
    Refund.objects.filter(pk=refund.pk).update(created_at=at(9, 10))
    Refund.objects.create(order=paid, amount=99, status="failed")
    report = services.sales(branch, week)
    assert report["gross"] == 0
    assert report["refunds"] == 500_000
    assert report["net"] == -500_000


def test_breakdown_totals_and_prep_time(branch, week) -> None:  # type: ignore[no-untyped-def]
    order(
        branch,
        placed=at(9, 12),
        discount_total=10_000,
        delivery_fee=150_000,
        vat_total=70_000,
        tip=20_000,
        accepted_at=at(9, 12, 5),
        ready_at=at(9, 12, 25),
        fulfilment_type="pickup",
    )
    order(branch, placed=at(9, 13), accepted_at=at(9, 13), ready_at=at(9, 13, 10))
    report = services.sales(branch, week)
    assert (report["discounts"], report["delivery_fees"], report["vat"], report["tips"]) == (
        10_000,
        150_000,
        70_000,
        20_000,
    )
    assert report["average_prep_minutes"] == 15.0
    assert report["by_fulfilment"]["pickup"]["orders"] == 1


def test_an_empty_period(branch, week) -> None:  # type: ignore[no-untyped-def]
    report = services.sales(branch, week)
    assert (
        report["orders"] == 0
        and report["average_order"] == 0
        and report["average_prep_minutes"] is None
    )
    assert len(report["daily"]) == 7
    assert services.peak_hours(branch, week)["busiest"] is None
    assert services.popular_items(branch, week) == []
    assert services.rider_performance(branch, week) == []


# ──────────────────────────────────────────────────────────────────────────────
# Items and peak hours
# ──────────────────────────────────────────────────────────────────────────────


def test_popular_items_come_from_what_was_sold(branch, week) -> None:  # type: ignore[no-untyped-def]
    first = order(branch, placed=at(10, 19))
    line(first, "Jollof", 2, 500_000, discount=100_000)
    line(first, "Suya", 1, 300_000)
    second = order(branch, placed=at(11, 20))
    line(second, "Jollof", 1, 500_000)
    unpaid = order(branch, placed=at(11, 21), payment="pending", status="pending_payment")
    line(unpaid, "Suya", 9, 300_000)

    items = services.popular_items(branch, week)
    assert items[0] == {
        "slug": "jollof",
        "name": "Jollof",
        "quantity": 3,
        "orders": 2,
        "revenue": 1_400_000,
    }
    assert items[1]["quantity"] == 1  # the unpaid nine are not sales
    assert len(services.popular_items(branch, week, limit=1)) == 1


def test_peak_hours_in_local_time(branch, week) -> None:  # type: ignore[no-untyped-def]
    for minute in (0, 10, 20):
        order(branch, placed=at(11, 19, minute))  # Friday 19:00 × 3
    order(branch, placed=at(12, 13))  # Saturday 13:00
    report = services.peak_hours(branch, week)
    assert report["grid"][4][19] == 3
    assert report["by_hour"][13] == 1
    assert report["busiest"] == {"weekday": "Friday", "hour": 19, "orders": 3}


# ──────────────────────────────────────────────────────────────────────────────
# Riders
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def riders(db):  # type: ignore[no-untyped-def]
    ade = RiderProfile.objects.create(
        user=User.objects.create_user(
            email="ade@example.com", password="x" * 16, full_name="Ade Rider"
        )
    )
    bola = RiderProfile.objects.create(
        user=User.objects.create_user(
            email="bola@example.com", password="x" * 16, full_name="Bola Rider"
        )
    )
    return ade, bola


def assign(
    o: Order,
    rider: RiderProfile,
    *,
    picked: dt.datetime | None,
    delivered: dt.datetime | None,
    cash: int | None = None,
) -> DeliveryAssignment:
    assignment = DeliveryAssignment.objects.create(
        order=o, rider=rider, picked_up_at=picked, delivered_at=delivered, cash_collected=cash
    )
    return assignment


def test_rider_performance(branch, week, riders) -> None:  # type: ignore[no-untyped-def]
    ade, bola = riders
    on_time = order(branch, placed=at(8, 12), estimated_delivery_at=at(8, 13))
    assign(on_time, ade, picked=at(8, 12, 30), delivered=at(8, 12, 50))
    late = order(
        branch, placed=at(8, 18), estimated_delivery_at=at(8, 19), method="cash", payment="unpaid"
    )
    assign(late, ade, picked=at(8, 18, 40), delivered=at(8, 19, 20), cash=1_000_000)
    no_estimate = order(branch, placed=at(9, 12))
    assign(no_estimate, ade, picked=None, delivered=at(9, 12, 30))

    failed = order(branch, placed=at(9, 18), status="failed_delivery")
    assign(failed, bola, picked=at(9, 18, 30), delivered=None)
    event = OrderStatusEvent.objects.create(
        order=failed, from_status="out_for_delivery", to_status="failed_delivery"
    )
    OrderStatusEvent.objects.filter(pk=event.pk).update(created_at=at(9, 19))

    report = services.rider_performance(branch, week)
    assert [row["rider"] for row in report] == ["Ade Rider", "Bola Rider"]
    ade_row, bola_row = report
    assert ade_row["deliveries"] == 3
    assert ade_row["on_time_percent"] == 50
    assert ade_row["cash_collected"] == 1_000_000
    assert ade_row["average_delivery_minutes"] is not None
    assert bola_row == {
        "rider": "Bola Rider",
        "deliveries": 0,
        "failed": 1,
        "cash_collected": 0,
        "average_delivery_minutes": None,
        "on_time_percent": None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# API, CSV, kitchen summary and admin
# ──────────────────────────────────────────────────────────────────────────────


def url(name: str) -> str:
    return reverse(f"v1:reporting:{name}")


def test_reports_are_for_managers(api_client, branch, verified_user, manager) -> None:  # type: ignore[no-untyped-def]
    for name in ("sales", "items", "peak-hours", "riders"):
        assert api_client.get(url(name)).status_code in {401, 403}
    api_client.force_authenticate(verified_user)
    assert api_client.get(url("sales")).status_code == 403
    api_client.force_authenticate(manager)
    for name in ("sales", "items", "peak-hours", "riders"):
        assert api_client.get(url(name)).status_code == 200


def test_sales_api_renders_money(api_client, branch, manager, riders) -> None:  # type: ignore[no-untyped-def]
    order(branch, placed=at(8, 12), total=2_000_000)
    api_client.force_authenticate(manager)
    body = api_client.get(url("sales"), {"from": "2026-09-07", "to": "2026-09-13"}).json()
    assert body["period"] == {"start": "2026-09-07", "end": "2026-09-13", "days": 7}
    assert body["gross"]["display"] == "₦20,000.00"
    assert body["by_payment_method"]["card"]["gross"]["amount"] == 2_000_000
    assert body["daily"][1]["gross"]["display"] == "₦20,000.00"


def test_bad_period_is_a_400(api_client, branch, manager) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(manager)
    response = api_client.get(url("items"), {"from": "nope"})
    assert response.status_code == 400
    assert "period" in response.json()["errors"]
    assert api_client.get(url("items"), {"limit": "lots"}).status_code == 400


def read_csv(response) -> list[list[str]]:  # type: ignore[no-untyped-def]
    assert response["Content-Type"].startswith("text/csv")
    return list(csv.reader(io.StringIO(response.content.decode())))


def test_csv_exports(api_client, branch, manager, riders) -> None:  # type: ignore[no-untyped-def]
    first = order(branch, placed=at(10, 19), total=1_250_050)
    line(first, "Jollof", 2, 500_000)
    assign(first, riders[0], picked=at(10, 19, 10), delivered=at(10, 19, 40), cash=None)
    api_client.force_authenticate(manager)
    params = {"from": "2026-09-07", "to": "2026-09-13", "export": "csv"}

    sales = api_client.get(url("sales"), params)
    assert 'filename="kuyash-sales-2026-09-07-to-2026-09-13.csv"' in sales["Content-Disposition"]
    rows = read_csv(sales)
    assert rows[0] == ["date", "orders", "gross_naira"]
    assert ["2026-09-10", "1", "12500.50"] in rows

    assert read_csv(api_client.get(url("items"), params))[1] == ["Jollof", "2", "1", "10000.00"]
    peak = read_csv(api_client.get(url("peak-hours"), params))
    assert peak[4][0] == "Thursday" and peak[4][20] == "1"
    assert read_csv(api_client.get(url("riders"), params))[1] == [
        "Ade Rider",
        "1",
        "0",
        "30.0",
        "",
        "0.00",
    ]


def test_rider_csv_with_no_timing(api_client, branch, manager, riders) -> None:  # type: ignore[no-untyped-def]
    failed = order(branch, placed=at(9, 18), status="failed_delivery")
    assign(failed, riders[1], picked=None, delivered=None)
    event = OrderStatusEvent.objects.create(order=failed, to_status="failed_delivery")
    OrderStatusEvent.objects.filter(pk=event.pk).update(created_at=at(9, 19))
    api_client.force_authenticate(manager)
    rows = read_csv(
        api_client.get(url("riders"), {"from": "2026-09-07", "to": "2026-09-13", "export": "csv"})
    )
    assert rows[1] == ["Bola Rider", "0", "1", "", "", "0.00"]


def test_kitchen_summary_uses_the_sales_definition(api_client, branch, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    kitchen = User.objects.create_user(email="k@example.com", password="x" * 16)
    kitchen.groups.add(Group.objects.get_or_create(name="kitchen")[0])
    now = at(9, 0, 30)
    monkeypatch.setattr("apps.core.models.Branch.local_now", lambda self: now)
    order(branch, placed=at(9, 0, 20), total=700_000)  # paid, just after local midnight
    order(
        branch,
        placed=at(9, 0, 25),
        total=900_000,
        method="cash",
        status="preparing",
        payment="unpaid",
    )
    api_client.force_authenticate(kitchen)
    body = api_client.get(reverse("v1:kds:summary")).json()
    assert body["todays_revenue"]["amount"] == 700_000


def test_admin_reports_page(client, branch, manager, riders) -> None:  # type: ignore[no-untyped-def]
    first = order(branch, placed=at(10, 19))
    line(first, "Jollof", 2, 500_000)
    assign(first, riders[0], picked=at(10, 19, 10), delivered=at(10, 19, 40))
    client.force_login(manager)
    index = client.get(reverse("admin:index"))
    assert "Reports" in index.content.decode()
    page = client.get(
        reverse("admin:reporting_report_changelist"), {"from": "2026-09-07", "to": "2026-09-13"}
    )
    content = page.content.decode()
    assert page.status_code == 200
    assert "Jollof" in content and "Ade Rider" in content and "busiest: Thursday 19:00" in content
    assert "/api/v1/reports/sales/?from=2026-09-07" in content

    bad = client.get(reverse("admin:reporting_report_changelist"), {"from": "garbage"})
    assert "Showing the last 7 days instead" in bad.content.decode()


def test_admin_reports_are_hidden_from_other_staff(client, branch) -> None:  # type: ignore[no-untyped-def]
    staff = User.objects.create_user(email="staff@example.com", password="x" * 16, is_staff=True)
    client.force_login(staff)
    assert "Reports" not in client.get(reverse("admin:index")).content.decode()
    assert client.get(reverse("admin:reporting_report_changelist")).status_code == 403


def test_report_admin_is_read_only(rf, manager) -> None:  # type: ignore[no-untyped-def]
    from django.contrib import admin

    from apps.reporting.models import Report

    model_admin = admin.site._registry[Report]
    request = rf.get("/")
    request.user = manager
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
    assert str(Report()) == "Reports"


# ──────────────────────────────────────────────────────────────────────────────
# CSV formula injection
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hostile",
    ["=cmd|'/c calc'!A1", "+1+1", "-2+3", "@SUM(A1)", "\tsneaky", "\rsneaky"],
)
def test_a_value_a_spreadsheet_would_run_is_neutralised(hostile: str) -> None:
    from apps.reporting.views import csv_cell

    assert csv_cell(hostile) == f"'{hostile}"


def test_ordinary_values_are_left_exactly_as_they_are() -> None:
    from apps.reporting.views import csv_cell

    assert csv_cell("Jollof") == "Jollof"
    assert csv_cell(12) == 12
    assert csv_cell("2026-09-10") == "2026-09-10"


def test_a_rider_cannot_smuggle_a_formula_into_a_managers_spreadsheet(  # type: ignore[no-untyped-def]
    api_client, branch, manager
) -> None:
    """Rider to manager, through a spreadsheet.

    `full_name` is set by the rider through `PATCH /accounts/me/` and nothing
    validates it. A manager opening the rider export in Excel used to get a DDE
    prompt — the lowest staff role reaching the highest.
    """
    hostile = "=cmd|'/c calc.exe'!A1"
    rider = RiderProfile.objects.create(
        user=User.objects.create_user(
            email="hostile@example.com", password="x" * 16, full_name=hostile
        )
    )
    delivered = order(branch, placed=at(10, 19))
    assign(delivered, rider, picked=at(10, 19, 10), delivered=at(10, 19, 40))

    api_client.force_authenticate(manager)
    rows = read_csv(
        api_client.get(url("riders"), {"from": "2026-09-07", "to": "2026-09-13", "export": "csv"})
    )

    assert rows[1][0] == f"'{hostile}"


# ──────────────────────────────────────────────────────────────────────────────
# The reports are SQL, not Python
# ──────────────────────────────────────────────────────────────────────────────


def query_cost(work) -> int:  # type: ignore[no-untyped-def]
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as captured:
        work()
    return len(captured)


def test_the_sales_report_does_not_grow_with_the_order_count(branch, week) -> None:  # type: ignore[no-untyped-def]
    """It used to pull every order of up to 366 days into Python and bucket them
    one row at a time, in a synchronous request."""
    for day in range(7, 13):
        order(branch, placed=at(day, 12))
    few = query_cost(lambda: services.sales(branch, week, refresh=True))

    for day in range(7, 13):
        for hour in range(10, 20):
            order(branch, placed=at(day, hour))
    many = query_cost(lambda: services.sales(branch, week, refresh=True))

    assert few == many


def test_peak_hours_does_not_grow_with_the_order_count(branch, week) -> None:  # type: ignore[no-untyped-def]
    order(branch, placed=at(11, 19))
    few = query_cost(lambda: services.peak_hours(branch, week))
    for day in range(7, 13):
        for hour in range(10, 20):
            order(branch, placed=at(day, hour))
    assert query_cost(lambda: services.peak_hours(branch, week)) == few == 1


def test_rider_performance_is_three_queries_whatever_the_volume(branch, week, riders) -> None:  # type: ignore[no-untyped-def]
    ade, _ = riders
    for day in range(8, 11):
        assign(
            order(branch, placed=at(day, 12)),
            ade,
            picked=at(day, 12, 10),
            delivered=at(day, 12, 40),
        )
    assert query_cost(lambda: services.rider_performance(branch, week)) == 3


def test_todays_sales_are_briefly_cached_for_the_kitchen_poll(branch, week) -> None:  # type: ignore[no-untyped-def]
    """The kitchen display asks for this every ten seconds, per screen."""
    order(branch, placed=at(8, 12), total=1_000_000)
    assert services.sales(branch, week)["orders"] == 1

    order(branch, placed=at(8, 13), total=2_000_000)
    assert services.sales(branch, week)["orders"] == 1  # served from the cache
    assert query_cost(lambda: services.sales(branch, week)) == 0

    assert services.sales(branch, week, refresh=True)["orders"] == 2
