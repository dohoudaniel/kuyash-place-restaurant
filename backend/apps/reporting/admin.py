"""The Reports page in the admin — where managers already work."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import urlencode

from apps.common.money import format_money
from apps.common.permissions import GROUP_MANAGERS, in_group
from apps.core.selectors import get_current_branch
from apps.reporting import services
from apps.reporting.models import Report


def _can_view(request: HttpRequest) -> bool:
    user = request.user
    return bool(
        user.is_active and user.is_staff and (user.is_superuser or in_group(user, GROUP_MANAGERS))
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    def has_module_permission(self, request: HttpRequest) -> bool:
        return _can_view(request)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return _can_view(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        if not _can_view(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        branch = get_current_branch()
        error = ""
        try:
            window = services.period(
                branch, start=request.GET.get("from", ""), end=request.GET.get("to", "")
            )
        except services.PeriodError as exc:
            error = str(exc)
            window = services.period(branch)

        sales = services.sales(branch, window)
        peak = services.peak_hours(branch, window)
        busiest_cell = max((max(day) for day in peak["grid"]), default=0) or 1
        query = urlencode(
            {"from": window.start.isoformat(), "to": window.end.isoformat(), "export": "csv"}
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "Reports",
            "opts": self.model._meta,
            "error": error,
            "window": window,
            "sales": sales,
            "money": {
                key: format_money(sales[key])
                for key in (
                    "gross",
                    "refunds",
                    "net",
                    "average_order",
                    "discounts",
                    "delivery_fees",
                    "vat",
                    "tips",
                )
            },
            "daily": [
                {**row, "gross_display": format_money(row["gross"])} for row in sales["daily"]
            ],
            "payment_methods": [
                {"name": name, "orders": b["orders"], "gross": format_money(b["gross"])}
                for name, b in sales["by_payment_method"].items()
            ],
            "items": [
                {**row, "revenue_display": format_money(row["revenue"])}
                for row in services.popular_items(branch, window, limit=15)
            ],
            "peak_rows": [
                {
                    "weekday": name,
                    "cells": [
                        {"count": count, "shade": round(count / busiest_cell, 2)}
                        for count in peak["grid"][index]
                    ],
                }
                for index, name in enumerate(peak["weekdays"])
            ],
            "hours": [f"{hour:02d}" for hour in range(24)],
            "busiest": peak["busiest"],
            "riders": [
                {**row, "cash_display": format_money(row["cash_collected"])}
                for row in services.rider_performance(branch, window)
            ],
            "csv": {
                name.replace("-", "_"): f"{reverse(f'v1:reporting:{name}')}?{query}"
                for name in ("sales", "items", "peak-hours", "riders")
            },
        }
        return TemplateResponse(request, "admin/reporting/reports.html", context)
