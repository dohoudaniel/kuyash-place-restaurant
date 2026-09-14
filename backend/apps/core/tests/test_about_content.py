"""About page content: settings figures, team and awards — only what staff publish."""

from __future__ import annotations

import io

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.about_seed import TEAM, seed_team
from apps.core.models import Award, SiteSettings, TeamMember

pytestmark = pytest.mark.django_db


def test_team_lists_only_published_people_in_order(api_client) -> None:  # type: ignore[no-untyped-def]
    TeamMember.objects.create(name="B", role="Chef", display_order=2)
    TeamMember.objects.create(name="A", role="Manager", bio="Runs the floor", display_order=1)
    TeamMember.objects.create(name="Hidden", role="Chef", is_active=False)
    body = api_client.get(reverse("v1:core:team")).json()
    assert body == [
        {"name": "A", "role": "Manager", "bio": "Runs the floor", "photo_url": None},
        {"name": "B", "role": "Chef", "bio": "", "photo_url": None},
    ]


def test_team_photos_are_served(api_client) -> None:  # type: ignore[no-untyped-def]
    from apps.gallery.tests.test_gallery import png

    TeamMember.objects.create(name="A", role="Chef", photo=png("a.png"))
    assert api_client.get(reverse("v1:core:team")).json()[0]["photo_url"].endswith(".png")


def test_awards_list_only_published_ones(api_client) -> None:  # type: ignore[no-untyped-def]
    Award.objects.create(
        title="Best Jollof", awarded_by="Lagos Food Fair", year=2025, url="https://example.com/a"
    )
    Award.objects.create(title="Hidden", awarded_by="Nobody", is_active=False)
    assert api_client.get(reverse("v1:core:awards")).json() == [
        {
            "title": "Best Jollof",
            "awarded_by": "Lagos Food Fair",
            "year": 2025,
            "url": "https://example.com/a",
        }
    ]


def test_settings_expose_the_established_year(api_client) -> None:  # type: ignore[no-untyped-def]
    row = SiteSettings.load()
    row.established_year = 2015
    row.save()
    assert api_client.get(reverse("v1:core:settings")).json()["established_year"] == 2015


def test_seed_team_is_inactive_and_idempotent() -> None:
    out = io.StringIO()
    assert seed_team(stdout=out) == len(TEAM)
    assert seed_team() == 0
    assert not TeamMember.objects.filter(is_active=True).exists()
    assert not TeamMember.objects.exclude(bio="").exists()
    assert not Award.objects.exists()
    assert "inactive until confirmed" in out.getvalue()


def test_labels_and_admin(client) -> None:  # type: ignore[no-untyped-def]
    member = TeamMember.objects.create(name="A", role="Chef")
    award = Award.objects.create(title="T", awarded_by="O")
    assert str(member) == "A — Chef"
    assert str(award) == "T — O"
    client.force_login(User.objects.create_superuser(email="root@example.com", password="x" * 16))
    for name in ("admin:core_teammember_changelist", "admin:core_award_changelist"):
        assert client.get(reverse(name)).status_code == 200
