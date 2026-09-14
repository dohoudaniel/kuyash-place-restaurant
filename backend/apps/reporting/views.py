"""Manager reports. JSON by default; ``?export=csv`` for a spreadsheet.

Not ``?format=csv``: DRF reserves ``format`` for content negotiation.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carts.serializers import money
from apps.common.permissions import IsManager
from apps.core.selectors import get_current_branch
from apps.reporting import services
from apps.reporting.serializers import (
    PeakHoursReportSerializer,
    PopularItemsReportSerializer,
    RiderReportSerializer,
    SalesReportSerializer,
)

PARAMETERS = [
    OpenApiParameter(
        "from",
        OpenApiTypes.DATE,
        required=False,
        description="First day, inclusive. Default: 6 days before `to`.",
    ),
    OpenApiParameter(
        "to", OpenApiTypes.DATE, required=False, description="Last day, inclusive. Default: today."
    ),
    OpenApiParameter("export", OpenApiTypes.STR, enum=["csv"], required=False),
]

MONEY_KEYS = (
    "gross",
    "refunds",
    "net",
    "average_order",
    "subtotal",
    "discounts",
    "delivery_fees",
    "service_charges",
    "vat",
    "tips",
)


def as_money(value: int) -> dict[str, Any]:
    return money(value)


def csv_response(
    name: str, window: services.Period, header: list[str], rows: list[list[Any]]
) -> HttpResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="kuyash-{name}-{window.start}-to-{window.end}.csv"'
    )
    return response


def naira(kobo: int) -> str:
    """Spreadsheet-friendly: plain naira with two decimals, no symbol."""
    return f"{kobo / 100:.2f}"


class ReportView(APIView):
    permission_classes = [IsManager]

    def window(self, request: Request) -> tuple[Any, services.Period]:
        branch = get_current_branch()
        try:
            return branch, services.period(
                branch,
                start=request.query_params.get("from", ""),
                end=request.query_params.get("to", ""),
            )
        except services.PeriodError as exc:
            raise serializers.ValidationError({"period": [str(exc)]}) from exc

    @staticmethod
    def period_payload(window: services.Period) -> dict[str, Any]:
        return {"start": window.start, "end": window.end, "days": window.days}

    @staticmethod
    def wants_csv(request: Request) -> bool:
        return request.query_params.get("export") == "csv"


class SalesReportView(ReportView):
    @extend_schema(
        summary="Sales, refunds and daily totals",
        parameters=PARAMETERS,
        responses={200: SalesReportSerializer},
        tags=["reports"],
    )
    def get(self, request: Request) -> Response | HttpResponse:
        branch, window = self.window(request)
        report = services.sales(branch, window)
        if self.wants_csv(request):
            return csv_response(
                "sales",
                window,
                ["date", "orders", "gross_naira"],
                [
                    [row["date"].isoformat(), row["orders"], naira(row["gross"])]
                    for row in report["daily"]
                ],
            )
        payload = {**report, "period": self.period_payload(window)}
        for key in MONEY_KEYS:
            payload[key] = as_money(report[key])
        for group in ("by_payment_method", "by_fulfilment"):
            payload[group] = {
                name: {"orders": b["orders"], "gross": as_money(b["gross"])}
                for name, b in report[group].items()
            }
        payload["daily"] = [
            {"date": row["date"], "orders": row["orders"], "gross": as_money(row["gross"])}
            for row in report["daily"]
        ]
        return Response(payload)


class PopularItemsReportView(ReportView):
    @extend_schema(
        summary="Best-selling dishes",
        parameters=[
            *PARAMETERS,
            OpenApiParameter(
                "limit", OpenApiTypes.INT, required=False, description="1–100, default 20."
            ),
        ],
        responses={200: PopularItemsReportSerializer},
        tags=["reports"],
    )
    def get(self, request: Request) -> Response | HttpResponse:
        branch, window = self.window(request)
        try:
            limit = max(1, min(100, int(request.query_params.get("limit", 20))))
        except ValueError as exc:
            raise serializers.ValidationError({"limit": ["Must be a whole number."]}) from exc
        items = services.popular_items(branch, window, limit=limit)
        if self.wants_csv(request):
            return csv_response(
                "popular-items",
                window,
                ["dish", "quantity", "orders", "revenue_naira"],
                [
                    [row["name"], row["quantity"], row["orders"], naira(row["revenue"])]
                    for row in items
                ],
            )
        return Response(
            {
                "period": self.period_payload(window),
                "items": [{**row, "revenue": as_money(row["revenue"])} for row in items],
            }
        )


class PeakHoursReportView(ReportView):
    @extend_schema(
        summary="Orders by weekday and hour",
        parameters=PARAMETERS,
        responses={200: PeakHoursReportSerializer},
        tags=["reports"],
    )
    def get(self, request: Request) -> Response | HttpResponse:
        branch, window = self.window(request)
        report = services.peak_hours(branch, window)
        if self.wants_csv(request):
            return csv_response(
                "peak-hours",
                window,
                ["weekday", *[f"{hour:02d}:00" for hour in range(24)]],
                [[name, *report["grid"][index]] for index, name in enumerate(report["weekdays"])],
            )
        return Response({"period": self.period_payload(window), **report})


class RiderReportView(ReportView):
    @extend_schema(
        summary="Rider performance",
        parameters=PARAMETERS,
        responses={200: RiderReportSerializer},
        tags=["reports"],
    )
    def get(self, request: Request) -> Response | HttpResponse:
        branch, window = self.window(request)
        riders = services.rider_performance(branch, window)
        if self.wants_csv(request):
            return csv_response(
                "riders",
                window,
                [
                    "rider",
                    "deliveries",
                    "failed",
                    "average_delivery_minutes",
                    "on_time_percent",
                    "cash_collected_naira",
                ],
                [
                    [
                        row["rider"],
                        row["deliveries"],
                        row["failed"],
                        ""
                        if row["average_delivery_minutes"] is None
                        else row["average_delivery_minutes"],
                        "" if row["on_time_percent"] is None else row["on_time_percent"],
                        naira(row["cash_collected"]),
                    ]
                    for row in riders
                ],
            )
        return Response(
            {
                "period": self.period_payload(window),
                "riders": [
                    {**row, "cash_collected": as_money(row["cash_collected"])} for row in riders
                ],
            }
        )
