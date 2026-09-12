"""Catalogue admin actions.

The repricing action is a launch-blocking control, not UI polish.
"""

from __future__ import annotations

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages import constants as message_levels
from django.test import RequestFactory

from apps.catalog.admin import MenuItemAdmin
from apps.catalog.models import MenuItem

pytestmark = pytest.mark.django_db


class _CollectingRequest:
    """A request stand-in that captures messages instead of needing middleware."""

    def __init__(self) -> None:
        self._request = RequestFactory().get("/admin/catalog/menuitem/")
        self.messages: list[tuple[str, int]] = []

    def __getattr__(self, name: str) -> object:
        return getattr(self._request, name)


@pytest.fixture
def admin_instance() -> MenuItemAdmin:
    return MenuItemAdmin(MenuItem, AdminSite())


def test_mark_repriced_clears_the_flag(admin_instance, unpriced_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    unpriced_item.base_price = 1_090_000
    unpriced_item.save()

    request = _CollectingRequest()
    admin_instance.message_user = lambda req, msg, level=20: request.messages.append((msg, level))  # type: ignore[assignment]
    admin_instance.mark_repriced(request, MenuItem.objects.filter(pk=unpriced_item.pk))  # type: ignore[arg-type]

    unpriced_item.refresh_from_db()
    assert unpriced_item.needs_repricing is False


def test_mark_repriced_refuses_items_priced_at_zero(  # type: ignore[no-untyped-def]
    admin_instance, branch, category
) -> None:
    """Clearing the flag on a ₦0.00 item would publish a free dish."""
    free = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Oops",
        slug="oops",
        base_price=0,
        needs_repricing=True,
    )
    request = _CollectingRequest()
    admin_instance.message_user = lambda req, msg, level=20: request.messages.append((msg, level))  # type: ignore[assignment]
    admin_instance.mark_repriced(request, MenuItem.objects.filter(pk=free.pk))  # type: ignore[arg-type]

    free.refresh_from_db()
    assert free.needs_repricing is True
    assert any(level == message_levels.ERROR for _, level in request.messages)


def test_eighty_six_actions_toggle_availability(admin_instance, menu_item: MenuItem) -> None:  # type: ignore[no-untyped-def]
    request = _CollectingRequest()
    admin_instance.message_user = lambda req, msg, level=20: None  # type: ignore[assignment]

    admin_instance.mark_unavailable(request, MenuItem.objects.filter(pk=menu_item.pk))  # type: ignore[arg-type]
    menu_item.refresh_from_db()
    assert menu_item.is_available_now is False

    admin_instance.mark_available(request, MenuItem.objects.filter(pk=menu_item.pk))  # type: ignore[arg-type]
    menu_item.refresh_from_db()
    assert menu_item.is_available_now is True


def test_repricing_flag_is_rendered_prominently(admin_instance, unpriced_item, menu_item) -> None:  # type: ignore[no-untyped-def]
    assert "PLACEHOLDER" in admin_instance.repricing_flag(unpriced_item)
    assert "confirmed" in admin_instance.repricing_flag(menu_item)
