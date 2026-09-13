"""Storage URL helpers.

Kept free of Django imports so the settings module can call it before apps load.
"""

from __future__ import annotations

from urllib.parse import urlparse


def supabase_public_domain(endpoint: str, bucket: str, override: str = "") -> str:
    """The host-and-path prefix public object URLs are served from.

    Supabase Storage has two faces. Writes go through the S3-compatible endpoint
    (``https://<ref>.supabase.co/storage/v1/s3``), which requires signed S3
    requests. Public reads go through ``/storage/v1/object/public/<bucket>/``.

    Without a custom domain, django-storages builds image URLs against the S3
    endpoint — ``…/storage/v1/s3/<bucket>/<key>`` — so every menu and gallery
    image would fail to load in production. Returned without a scheme, which is
    the form ``AWS_S3_CUSTOM_DOMAIN`` expects.
    """
    if override:
        return override.removeprefix("https://").removeprefix("http://").rstrip("/")
    host = urlparse(endpoint).netloc
    if not host or not bucket:
        return ""
    return f"{host}/storage/v1/object/public/{bucket}"
