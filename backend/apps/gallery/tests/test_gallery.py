"""Gallery: published photos, filters, neighbours and safe uploads.

Replaces 20 hardcoded entries whose image keys had no files behind them.
"""

from __future__ import annotations

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User
from apps.core.models import Branch
from apps.gallery.models import MAX_IMAGE_BYTES, GalleryImage, GalleryTag, validate_image_size

pytestmark = pytest.mark.django_db

LIST = reverse("v1:gallery:list")


def png(name: str = "photo.png") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def photo(
    branch: Branch, title: str, category: str = "food", order: int = 0, **extra
) -> GalleryImage:  # type: ignore[no-untyped-def]
    tags = extra.pop("tags", [])
    image = GalleryImage.objects.create(
        branch=branch, title=title, category=category, image=png(), display_order=order, **extra
    )
    image.tags.set(tags)
    return image


def detail_url(image: GalleryImage) -> str:
    return reverse("v1:gallery:detail", kwargs={"image_id": image.pk})


@pytest.fixture
def signature(db) -> GalleryTag:  # type: ignore[no-untyped-def]
    return GalleryTag.objects.create(name="Signature", slug="signature")


def test_the_list_shows_published_photos_in_display_order(api_client, branch, signature) -> None:  # type: ignore[no-untyped-def]
    photo(branch, "Second", order=2)
    photo(
        branch, "First", order=1, tags=[signature], description="Smoky", alt_text="A bowl of jollof"
    )
    photo(branch, "Hidden", is_active=False)

    body = api_client.get(LIST).json()

    assert [row["title"] for row in body] == ["First", "Second"]
    first = body[0]
    assert first["category"] == "food"
    assert first["category_display"] == "Food"
    assert first["tags"] == [{"slug": "signature", "name": "Signature"}]
    assert first["alt_text"] == "A bowl of jollof"
    assert first["image_url"].endswith(".png")
    assert body[1]["alt_text"] == "Second"  # falls back to the title


def test_another_branchs_photos_are_not_shown(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    elsewhere = Branch.objects.create(
        name="Elsewhere", slug="elsewhere", city="Abuja", state="FCT", is_active=False
    )
    photo(elsewhere, "Not ours")
    photo(branch, "Ours")
    assert [row["title"] for row in api_client.get(LIST).json()] == ["Ours"]


def test_filters(api_client, branch, signature) -> None:  # type: ignore[no-untyped-def]
    photo(branch, "Jollof", tags=[signature], is_featured=True)
    photo(branch, "Suya")
    photo(branch, "Patio", category="interior")

    def titles(**params):  # type: ignore[no-untyped-def]
        return sorted(row["title"] for row in api_client.get(LIST, params).json())

    assert titles(category="interior") == ["Patio"]
    assert titles(tag="signature") == ["Jollof"]
    assert titles(featured="true") == ["Jollof"]
    assert titles(category="food", tag="signature") == ["Jollof"]


def test_an_unknown_category_is_refused(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(LIST, {"category": "cars"})
    assert response.status_code == 400
    assert "category" in response.json()["errors"]


def test_detail_carries_neighbours(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    a = photo(branch, "A", order=1)
    b = photo(branch, "B", order=2)
    c = photo(branch, "C", order=3, category="team")

    middle = api_client.get(detail_url(b)).json()
    assert middle["previous_id"] == str(a.pk)
    assert middle["next_id"] == str(c.pk)

    first = api_client.get(detail_url(a)).json()
    assert first["previous_id"] is None

    # Neighbours follow the filter the visitor is browsing with.
    in_food = api_client.get(detail_url(b), {"category": "food"}).json()
    assert in_food["next_id"] is None


def test_hidden_or_filtered_out_photos_are_not_found(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    hidden = photo(branch, "Hidden", is_active=False)
    team = photo(branch, "Team", category="team")
    assert api_client.get(detail_url(hidden)).status_code == 404
    assert api_client.get(detail_url(team), {"category": "food"}).status_code == 404


def test_svg_uploads_are_refused(branch) -> None:  # type: ignore[no-untyped-def]
    image = GalleryImage(
        branch=branch,
        title="Sneaky",
        category="food",
        image=SimpleUploadedFile(
            "x.svg", b"<svg onload='alert(1)'/>", content_type="image/svg+xml"
        ),
    )
    with pytest.raises(ValidationError) as caught:
        image.full_clean()
    assert "image" in caught.value.message_dict


def test_oversized_photos_are_refused() -> None:
    class Big:
        size = MAX_IMAGE_BYTES + 1

    with pytest.raises(ValidationError):
        validate_image_size(Big())
    validate_image_size(type("Ok", (), {"size": MAX_IMAGE_BYTES})())


def test_labels(branch, signature) -> None:  # type: ignore[no-untyped-def]
    assert str(photo(branch, "Jollof")) == "Jollof"
    assert str(signature) == "Signature"


@pytest.fixture
def admin_client_logged_in(client, db):  # type: ignore[no-untyped-def]
    admin = User.objects.create_superuser(email="root@example.com", password="x" * 16)
    client.force_login(admin)
    return client


def test_admin_lists_and_previews_photos(admin_client_logged_in, branch) -> None:  # type: ignore[no-untyped-def]
    image = photo(branch, "Jollof")
    changelist = admin_client_logged_in.get(reverse("admin:gallery_galleryimage_changelist"))
    assert changelist.status_code == 200
    assert image.image.url in changelist.content.decode()

    change = admin_client_logged_in.get(
        reverse("admin:gallery_galleryimage_change", args=[image.pk])
    )
    assert change.status_code == 200
    assert "max-height:240px" in change.content.decode()


def test_admin_add_form_defaults_to_the_current_branch(admin_client_logged_in, branch) -> None:  # type: ignore[no-untyped-def]
    response = admin_client_logged_in.get(reverse("admin:gallery_galleryimage_add"))
    assert response.status_code == 200
    assert response.context["adminform"].form.initial["branch"] == str(branch.pk)


def test_admin_upload_creates_a_photo(admin_client_logged_in, branch, signature) -> None:  # type: ignore[no-untyped-def]
    response = admin_client_logged_in.post(
        reverse("admin:gallery_galleryimage_add"),
        {
            "branch": str(branch.pk),
            "category": "events",
            "title": "Wedding",
            "image": png("wedding.png"),
            "tags": [signature.pk],
            "display_order": 0,
            "is_active": "on",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    created = GalleryImage.objects.get(title="Wedding")
    assert list(created.tags.all()) == [signature]
