"""Supabase public URL derivation.

Without this, django-storages points image URLs at the S3 endpoint, which
needs signed requests — every menu photo would fail to load in production.
"""

from __future__ import annotations

from storages.backends.s3 import S3Storage

from apps.common.storage import supabase_public_domain

ENDPOINT = "https://abcd1234.supabase.co/storage/v1/s3"


def test_derives_the_public_object_path_from_the_s3_endpoint() -> None:
    assert (
        supabase_public_domain(ENDPOINT, "menu")
        == "abcd1234.supabase.co/storage/v1/object/public/menu"
    )


def test_an_explicit_override_wins_and_loses_its_scheme() -> None:
    assert supabase_public_domain(ENDPOINT, "menu", "https://cdn.example.com/") == "cdn.example.com"
    assert supabase_public_domain(ENDPOINT, "menu", "http://cdn.example.com") == "cdn.example.com"


def test_nothing_is_derived_without_an_endpoint_or_bucket() -> None:
    assert supabase_public_domain("", "menu") == ""
    assert supabase_public_domain(ENDPOINT, "") == ""


def test_storage_urls_use_the_public_path_not_the_s3_endpoint() -> None:
    """The actual regression: what an image URL looks like end to end."""
    storage = S3Storage(
        access_key="x",
        secret_key="y",
        bucket_name="menu",
        endpoint_url=ENDPOINT,
        addressing_style="path",
        querystring_auth=False,
        custom_domain=supabase_public_domain(ENDPOINT, "menu"),
    )
    url = storage.url("items/burger.jpg")
    assert url == "https://abcd1234.supabase.co/storage/v1/object/public/menu/items/burger.jpg"
    assert "/storage/v1/s3/" not in url
