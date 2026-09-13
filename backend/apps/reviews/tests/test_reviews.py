"""Reviews: verified purchase, moderation, the edit window and aggregates.

Replaces a modal that promised moderation, logged the review to the console and
was mounted nowhere, beside five hardcoded stars on every dish.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import anonymise_user
from apps.catalog.models import MenuItem
from apps.orders.models import Order, OrderItem
from apps.orders.services.placement import place_order
from apps.reviews import services
from apps.reviews.models import Review, ReviewHelpfulVote, ReviewStatus
from apps.reviews.services import AlreadyReviewed, EditWindowClosed, OwnReview, ReviewNotAllowed

pytestmark = pytest.mark.django_db

LIST = reverse("v1:reviews:list")
PENDING = reverse("v1:reviews:pending")


def detail_url(review: Review) -> str:
    return reverse("v1:reviews:detail", kwargs={"review_id": review.pk})


def helpful_url(review: Review) -> str:
    return reverse("v1:reviews:helpful", kwargs={"review_id": review.pk})


def moderate_url(review: Review) -> str:
    return reverse("v1:reviews:moderate", kwargs={"review_id": review.pk})


def deliver(order: Order) -> Order:
    Order.objects.filter(pk=order.pk).update(status="delivered", delivered_at=timezone.now())
    order.refresh_from_db()
    return order


@pytest.fixture
def order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    return place_order(cart=ready_cart, payment_method="card")


@pytest.fixture
def line(order) -> OrderItem:  # type: ignore[no-untyped-def]
    deliver(order)
    return order.items.get()


@pytest.fixture
def manager(db) -> User:  # type: ignore[no-untyped-def]
    user = User.objects.create_user(
        email="mgr@example.com", password="x" * 16, full_name="Mo Manager"
    )
    user.groups.add(Group.objects.get_or_create(name="managers")[0])
    return user


@pytest.fixture
def stranger(db) -> User:  # type: ignore[no-untyped-def]
    return User.objects.create_user(
        email="stranger@example.com", password="x" * 16, full_name="Sam Stone"
    )


def burger() -> MenuItem:
    return MenuItem.objects.get(slug="classic-smash-burger")


def write(line: OrderItem, rating: int = 5, **extra) -> Review:  # type: ignore[no-untyped-def]
    return services.create_review(
        user=line.order.user,
        order_line_id=line.public_id,
        rating=rating,
        title=extra.get("title", "Proper burger"),
        comment=extra.get("comment", "Crisp edges, soft bun."),
        recommends=extra.get("recommends", True),
    )


def extra_review(line: OrderItem, rating: int, email: str) -> Review:
    """Another customer's approved review of the same dish."""
    user = User.objects.create_user(email=email, password="x" * 16, full_name="Other Person")
    review = Review.objects.create(
        user=user, menu_item=line.menu_item, rating=rating, title="t", comment="c"
    )
    services.moderate(review, moderator=None, approve=True)
    return review


# ──────────────────────────────────────────────────────────────────────────────
# Who may review (REV-1, REV-5)
# ──────────────────────────────────────────────────────────────────────────────


def test_a_delivered_line_can_be_reviewed(line) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=4)
    assert review.status == ReviewStatus.PENDING
    assert review.is_verified_purchase
    assert review.menu_item == burger()
    assert review.order == line.order


def test_nothing_counts_until_approved(line) -> None:  # type: ignore[no-untyped-def]
    write(line)
    item = burger()
    assert item.review_count == 0
    assert item.average_rating is None


def test_an_undelivered_order_cannot_be_reviewed(order) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReviewNotAllowed):
        write(order.items.get())


def test_a_refund_before_delivery_is_still_not_reviewable(order) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(status="refunded")
    with pytest.raises(ReviewNotAllowed):
        write(order.items.get())


def test_someone_elses_line_is_not_found(line, stranger) -> None:  # type: ignore[no-untyped-def]
    from django.http import Http404

    with pytest.raises(Http404):
        services.create_review(
            user=stranger, order_line_id=line.public_id, rating=5, title="t", comment="c"
        )


def test_one_review_per_line(line) -> None:  # type: ignore[no-untyped-def]
    write(line)
    with pytest.raises(AlreadyReviewed):
        write(line)


def test_a_dish_removed_from_the_menu_cannot_be_reviewed(line) -> None:  # type: ignore[no-untyped-def]
    OrderItem.objects.filter(pk=line.pk).update(menu_item=None)
    line.refresh_from_db()
    with pytest.raises(ReviewNotAllowed):
        write(line)


# ──────────────────────────────────────────────────────────────────────────────
# Moderation and aggregates (REV-3, REV-4)
# ──────────────────────────────────────────────────────────────────────────────


def test_approval_updates_the_dish_rating(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=4)
    services.moderate(review, moderator=manager, approve=True)
    item = burger()
    assert item.review_count == 1
    assert item.average_rating == Decimal("4.0")
    review.refresh_from_db()
    assert review.moderated_by == manager
    assert review.moderated_at is not None


@pytest.mark.parametrize(("ratings", "expected"), [((5, 4, 4), "4.3"), ((5, 5, 4), "4.7")])
def test_the_average_rounds_half_up_to_one_place(line, ratings, expected) -> None:  # type: ignore[no-untyped-def]
    for index, rating in enumerate(ratings):
        extra_review(line, rating, f"r{index}@example.com")
    assert burger().average_rating == Decimal(expected)
    assert burger().review_count == 3


def test_taking_down_an_approved_review_corrects_the_rating(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=1)
    extra_review(line, 5, "fan@example.com")
    services.moderate(review, moderator=manager, approve=True)
    assert burger().average_rating == Decimal("3.0")

    services.moderate(review, moderator=manager, approve=False, reason="Not about the food.")
    item = burger()
    assert item.average_rating == Decimal("5.0")
    assert item.review_count == 1
    review.refresh_from_db()
    assert review.rejection_reason == "Not about the food."


def test_the_last_review_going_leaves_the_dish_unrated(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    services.delete_review(review)
    item = burger()
    assert item.review_count == 0
    assert item.average_rating is None


def test_recompute_ignores_a_missing_item() -> None:
    services.recompute_item_rating(None)  # no error, nothing to do


# ──────────────────────────────────────────────────────────────────────────────
# The edit window
# ──────────────────────────────────────────────────────────────────────────────


def test_an_edit_returns_the_review_to_moderation(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=5)
    services.moderate(review, moderator=manager, approve=True)

    services.update_review(review, rating=2, comment="Changed my mind.")

    review.refresh_from_db()
    assert review.status == ReviewStatus.PENDING
    assert review.moderated_by is None
    assert review.comment == "Changed my mind."
    assert burger().review_count == 0  # the edited text has not been read yet


def test_edits_close_after_the_window(line, settings) -> None:  # type: ignore[no-untyped-def]
    settings.REVIEW_EDIT_WINDOW_DAYS = 7
    review = write(line)
    Review.objects.filter(pk=review.pk).update(created_at=timezone.now() - dt.timedelta(days=8))
    review.refresh_from_db()
    assert not services.can_edit(review)
    with pytest.raises(EditWindowClosed):
        services.update_review(review, rating=1)


def test_the_window_is_configurable(line, settings) -> None:  # type: ignore[no-untyped-def]
    settings.REVIEW_EDIT_WINDOW_DAYS = 30
    review = write(line)
    Review.objects.filter(pk=review.pk).update(created_at=timezone.now() - dt.timedelta(days=8))
    review.refresh_from_db()
    assert services.can_edit(review)


# ──────────────────────────────────────────────────────────────────────────────
# Helpful votes
# ──────────────────────────────────────────────────────────────────────────────


def test_a_voter_counts_once(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    assert services.mark_helpful(review, voter_key="anon:a") == (1, True)
    assert services.mark_helpful(review, voter_key="anon:a") == (1, False)
    assert services.mark_helpful(review, voter_key="anon:b") == (2, True)


def test_authors_cannot_vote_for_themselves(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    with pytest.raises(OwnReview):
        services.mark_helpful(review, voter_key="user:x", user=line.order.user)


def test_unpublished_reviews_cannot_be_voted_on(line) -> None:  # type: ignore[no-untyped-def]
    from django.http import Http404

    with pytest.raises(Http404):
        services.mark_helpful(write(line), voter_key="anon:a")


# ──────────────────────────────────────────────────────────────────────────────
# Privacy
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("full_name", "shown"),
    [("Ada Chioma Obi", "Ada O."), ("Ada", "Ada"), ("", "Kuyash guest")],
)
def test_authors_are_shown_by_first_name_and_initial(line, full_name, shown) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    review.user.full_name = full_name
    assert services.author_name(review) == shown


def test_erasure_removes_reviews_and_their_effect(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    assert burger().review_count == 1

    anonymise_user(line.order.user)

    assert not Review.objects.exists()
    assert burger().review_count == 0


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────


def test_post_creates_a_pending_review(api_client, line, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    response = api_client.post(
        LIST,
        {
            "order_line": str(line.public_id),
            "rating": 5,
            "title": " Great ",
            "comment": "Loved it.",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "pending"
    assert body["title"] == "Great"
    assert body["author_name"] == "Ada O."
    assert body["menu_item"] == {"slug": "classic-smash-burger", "name": "Classic Smash Burger"}
    assert body["order_reference"] == line.order.reference
    assert body["can_edit"] is True


def test_posting_requires_sign_in(api_client, line) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(LIST, {"order_line": str(line.public_id)}, format="json")
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("rating", [0, 6])
def test_ratings_outside_one_to_five_are_refused(api_client, line, verified_user, rating) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    response = api_client.post(
        LIST,
        {"order_line": str(line.public_id), "rating": rating, "title": "t", "comment": "c"},
        format="json",
    )
    assert response.status_code == 400
    assert "rating" in response.json()["errors"]


def test_undelivered_orders_get_a_stable_code(api_client, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    response = api_client.post(
        LIST,
        {"order_line": str(order.items.get().public_id), "rating": 5, "title": "t", "comment": "c"},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["code"] == "review_not_allowed"


def test_the_public_list_shows_only_approved_reviews(api_client, line, manager) -> None:  # type: ignore[no-untyped-def]
    write(line, title="Still pending")
    extra_review(line, 4, "one@example.com")
    popular = extra_review(line, 3, "two@example.com")
    Review.objects.filter(pk=popular.pk).update(helpful_count=9)

    response = api_client.get(LIST, {"item": "classic-smash-burger", "sort": "helpful"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [row["rating"] for row in body["results"]] == [3, 4]
    assert "status" not in body["results"][0]
    assert "Still pending" not in str(body)


def test_the_list_needs_a_dish(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get(LIST)
    assert response.status_code == 400
    assert "item" in response.json()["errors"]


def test_authors_can_read_edit_and_delete_their_review(api_client, line, verified_user) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    api_client.force_authenticate(verified_user)

    assert api_client.get(detail_url(review)).json()["id"] == str(review.pk)

    response = api_client.patch(detail_url(review), {"rating": 3}, format="json")
    assert response.status_code == 200
    review.refresh_from_db()
    assert review.rating == 3
    assert review.title == "Proper burger"  # untouched fields stay

    assert api_client.delete(detail_url(review)).status_code == 204
    assert not Review.objects.exists()


def test_other_customers_cannot_touch_a_review(api_client, line, stranger) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    api_client.force_authenticate(stranger)
    assert api_client.patch(detail_url(review), {"rating": 1}, format="json").status_code == 404
    assert api_client.delete(detail_url(review)).status_code == 404


def test_a_closed_window_is_reported(api_client, line, verified_user) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    Review.objects.filter(pk=review.pk).update(created_at=timezone.now() - dt.timedelta(days=30))
    api_client.force_authenticate(verified_user)
    response = api_client.patch(detail_url(review), {"rating": 1}, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "edit_window_closed"


def test_anonymous_helpful_votes_count_once_per_address(api_client, line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)

    first = api_client.post(helpful_url(review), REMOTE_ADDR="198.51.100.7")
    again = api_client.post(helpful_url(review), REMOTE_ADDR="198.51.100.7")
    other = api_client.post(helpful_url(review), REMOTE_ADDR="198.51.100.8")

    assert first.json() == {"helpful_count": 1, "counted": True}
    assert again.json() == {"helpful_count": 1, "counted": False}
    assert other.json() == {"helpful_count": 2, "counted": True}
    assert not ReviewHelpfulVote.objects.filter(voter_key__contains="198.51").exists()


def test_signed_in_authors_cannot_vote_on_their_own(
    api_client, line, manager, verified_user
) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    api_client.force_authenticate(verified_user)
    response = api_client.post(helpful_url(review))
    assert response.status_code == 409
    assert response.json()["code"] == "own_review"


def test_the_moderation_queue_is_for_managers(api_client, line, verified_user, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)

    api_client.force_authenticate(verified_user)
    assert api_client.get(PENDING).status_code == 403
    assert (
        api_client.post(moderate_url(review), {"action": "approve"}, format="json").status_code
        == 403
    )

    api_client.force_authenticate(manager)
    queue = api_client.get(PENDING).json()
    assert [row["id"] for row in queue["results"]] == [str(review.pk)]

    response = api_client.post(moderate_url(review), {"action": "approve"}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert burger().review_count == 1


def test_rejection_needs_a_reason(api_client, line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    api_client.force_authenticate(manager)
    response = api_client.post(
        moderate_url(review), {"action": "reject", "reason": "  "}, format="json"
    )
    assert response.status_code == 400
    assert "reason" in response.json()["errors"]


def test_order_lines_say_whether_they_can_be_reviewed(api_client, line, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    url = reverse("v1:orders:detail", kwargs={"reference": line.order.reference})

    before = api_client.get(url).json()["items"][0]
    assert before["id"] == str(line.public_id)
    assert before["can_review"] is True
    assert before["review"] is None

    review = write(line, rating=4)
    after = api_client.get(url).json()["items"][0]
    assert after["can_review"] is False
    assert after["review"] == {"id": str(review.pk), "status": "pending", "rating": 4}


def test_undelivered_lines_are_not_reviewable(api_client, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    url = reverse("v1:orders:detail", kwargs={"reference": order.reference})
    assert api_client.get(url).json()["items"][0]["can_review"] is False


# ──────────────────────────────────────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client_logged_in(client, db):  # type: ignore[no-untyped-def]
    admin = User.objects.create_superuser(email="root@example.com", password="x" * 16)
    client.force_login(admin)
    return client


def test_admin_approval_updates_the_rating(admin_client_logged_in, line) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=4)
    response = admin_client_logged_in.post(
        reverse("admin:reviews_review_changelist"),
        {"action": "approve_selected", "_selected_action": [str(review.pk)]},
    )
    assert response.status_code == 302
    assert burger().average_rating == Decimal("4.0")


def test_admin_rejection_without_a_reason_is_refused(admin_client_logged_in, line) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    url = reverse("admin:reviews_review_change", args=[review.pk])
    response = admin_client_logged_in.post(url, {"status": "rejected", "rejection_reason": ""})
    assert response.status_code == 200  # the form is shown again with an error
    review.refresh_from_db()
    assert review.status == ReviewStatus.PENDING

    response = admin_client_logged_in.post(url, {"status": "rejected", "rejection_reason": "Spam."})
    assert response.status_code == 302
    review.refresh_from_db()
    assert review.status == ReviewStatus.REJECTED


def test_admin_delete_corrects_the_rating(admin_client_logged_in, line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    response = admin_client_logged_in.post(
        reverse("admin:reviews_review_delete", args=[review.pk]), {"post": "yes"}
    )
    assert response.status_code == 302
    assert burger().review_count == 0


def test_a_double_submit_that_races_the_check_is_still_refused(line) -> None:  # type: ignore[no-untyped-def]
    from unittest import mock

    from django.db.models import QuerySet

    write(line)
    with mock.patch.object(QuerySet, "exists", return_value=False), pytest.raises(AlreadyReviewed):
        write(line)


def test_vote_labels(line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line, rating=4, title="Nice")
    services.moderate(review, moderator=manager, approve=True)
    services.mark_helpful(review, voter_key="anon:z")
    assert str(review) == "4★ Nice"
    assert str(ReviewHelpfulVote.objects.get()) == f"anon:z → {review.pk}"


def test_admin_returning_a_review_to_pending_corrects_the_rating(
    admin_client_logged_in, line, manager
) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    url = reverse("admin:reviews_review_change", args=[review.pk])
    response = admin_client_logged_in.post(url, {"status": "pending", "rejection_reason": ""})
    assert response.status_code == 302
    assert burger().review_count == 0


def test_admin_bulk_delete_corrects_the_rating(admin_client_logged_in, line, manager) -> None:  # type: ignore[no-untyped-def]
    review = write(line)
    services.moderate(review, moderator=manager, approve=True)
    response = admin_client_logged_in.post(
        reverse("admin:reviews_review_changelist"),
        {"action": "delete_selected", "_selected_action": [str(review.pk)], "post": "yes"},
    )
    assert response.status_code == 302
    assert not Review.objects.exists()
    assert burger().review_count == 0
