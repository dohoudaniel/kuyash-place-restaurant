"""Wishlist.

Replaces `lib/store/wishlistStore.ts`, which keeps the list in localStorage —
lost on a new device, a cleared browser or a private window.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.catalog.models import MenuItem, WishlistItem

pytestmark = pytest.mark.django_db

LIST = "v1:wishlist:wishlist"


def test_saving_a_dish(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(reverse(LIST), {"menu_item": menu_item.slug}, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["slug"] == menu_item.slug


def test_saving_twice_is_not_an_error(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    """The customer wanted it saved, and it is."""
    api_client.force_authenticate(user=verified_user)
    api_client.post(reverse(LIST), {"menu_item": menu_item.slug}, format="json")
    response = api_client.post(reverse(LIST), {"menu_item": menu_item.slug}, format="json")

    assert response.status_code == 201
    assert response.json()["count"] == 1
    assert WishlistItem.objects.count() == 1


def test_the_wishlist_is_scoped_to_the_caller(api_client, verified_user, menu_item, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    other = User.objects.create_user(
        email="other@example.com", password="correct-horse-battery-staple"
    )
    WishlistItem.objects.create(user=other, menu_item=menu_item)

    api_client.force_authenticate(user=verified_user)
    assert api_client.get(reverse(LIST)).json()["count"] == 0


def test_removing_a_dish(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    api_client.post(reverse(LIST), {"menu_item": menu_item.slug}, format="json")

    response = api_client.delete(
        reverse("v1:wishlist:wishlist-item", kwargs={"slug": menu_item.slug})
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_removing_something_not_saved_is_harmless(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.delete(
        reverse("v1:wishlist:wishlist-item", kwargs={"slug": menu_item.slug})
    )
    assert response.status_code == 200


def test_a_withdrawn_dish_drops_out_of_the_list(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    """A saved item pulled from the menu must not be offered back."""
    api_client.force_authenticate(user=verified_user)
    api_client.post(reverse(LIST), {"menu_item": menu_item.slug}, format="json")

    menu_item.is_active = False
    menu_item.save()

    assert api_client.get(reverse(LIST)).json()["count"] == 0


def test_a_placeholder_priced_dish_cannot_be_saved(
    api_client, verified_user, unpriced_item
) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(reverse(LIST), {"menu_item": unpriced_item.slug}, format="json")
    assert response.status_code == 404


def test_the_wishlist_requires_authentication(api_client, menu_item) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse(LIST)).status_code in (401, 403)


# ── Sync on first sign-in ─────────────────────────────────────────────────────


def test_syncing_merges_a_browser_list(
    api_client, verified_user, menu_item, branch, category
) -> None:  # type: ignore[no-untyped-def]
    second = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Loaded Fries",
        slug="loaded-fries",
        base_price=320_000,
        needs_repricing=False,
    )
    api_client.force_authenticate(user=verified_user)

    response = api_client.post(
        reverse("v1:wishlist:wishlist-sync"),
        {"menu_items": [menu_item.slug, second.slug]},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_syncing_is_additive(api_client, verified_user, menu_item, branch, category) -> None:  # type: ignore[no-untyped-def]
    """Signing in must never lose something saved on either side."""
    second = MenuItem.objects.create(
        branch=branch,
        category=category,
        name="Loaded Fries",
        slug="loaded-fries",
        base_price=320_000,
        needs_repricing=False,
    )
    WishlistItem.objects.create(user=verified_user, menu_item=second)

    api_client.force_authenticate(user=verified_user)
    body = api_client.post(
        reverse("v1:wishlist:wishlist-sync"), {"menu_items": [menu_item.slug]}, format="json"
    ).json()

    assert body["count"] == 2
    assert {row["slug"] for row in body["items"]} == {menu_item.slug, second.slug}


def test_stale_slugs_are_reported_not_silently_dropped(  # type: ignore[no-untyped-def]
    api_client, verified_user, menu_item
) -> None:
    """The frontend's list is keyed on an image filename, so it will contain
    entries that no longer match anything."""
    api_client.force_authenticate(user=verified_user)
    body = api_client.post(
        reverse("v1:wishlist:wishlist-sync"),
        {"menu_items": [menu_item.slug, "signatureGrillPlate", "gone-forever"]},
        format="json",
    ).json()

    assert body["count"] == 1
    assert set(body["unmatched"]) == {"signatureGrillPlate", "gone-forever"}


def test_syncing_an_empty_list_is_allowed(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    response = api_client.post(
        reverse("v1:wishlist:wishlist-sync"), {"menu_items": []}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_duplicate_slugs_in_a_sync_are_collapsed(api_client, verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(user=verified_user)
    body = api_client.post(
        reverse("v1:wishlist:wishlist-sync"),
        {"menu_items": [menu_item.slug, menu_item.slug, menu_item.slug]},
        format="json",
    ).json()
    assert body["count"] == 1


def test_string_representation(verified_user, menu_item) -> None:  # type: ignore[no-untyped-def]
    entry = WishlistItem.objects.create(user=verified_user, menu_item=menu_item)
    assert "ada@example.com" in str(entry)
