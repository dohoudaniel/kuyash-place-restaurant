"""Review rules: who may review, the edit window, moderation and aggregates."""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F
from django.http import Http404
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import DomainError
from apps.orders.models import OrderItem
from apps.reviews.models import Review, ReviewHelpfulVote, ReviewStatus


class ReviewNotAllowed(DomainError):
    code = "review_not_allowed"
    status_code = status.HTTP_409_CONFLICT
    title = "This dish can't be reviewed yet"


class AlreadyReviewed(DomainError):
    code = "already_reviewed"
    status_code = status.HTTP_409_CONFLICT
    title = "You have already reviewed this dish from this order"


class EditWindowClosed(DomainError):
    code = "edit_window_closed"
    status_code = status.HTTP_409_CONFLICT
    title = "This review can no longer be edited"


class OwnReview(DomainError):
    code = "own_review"
    status_code = status.HTTP_409_CONFLICT
    title = "You can't mark your own review as helpful"


RATING_STEP = Decimal("0.1")


def edit_window() -> dt.timedelta:
    return dt.timedelta(days=settings.REVIEW_EDIT_WINDOW_DAYS)


def editable_until(review: Review) -> dt.datetime:
    return review.created_at + edit_window()


def can_edit(review: Review, *, now: dt.datetime | None = None) -> bool:
    return (now or timezone.now()) < editable_until(review)


def author_name(review: Review) -> str:
    """First name and last initial — enough to feel human, not enough to find someone."""
    parts = (review.user.full_name or "").split()
    if not parts:
        return "Kuyash guest"
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."


def recompute_item_rating(menu_item_id: Any) -> None:
    """Rebuild a dish's rating from its approved reviews (REV-4).

    Recomputed from scratch rather than nudged up and down, so a moderation
    change, an edit or a deletion can never leave the figure drifting.
    """
    from apps.catalog.models import MenuItem

    if menu_item_id is None:
        return
    figures = Review.objects.filter(
        menu_item_id=menu_item_id, status=ReviewStatus.APPROVED
    ).aggregate(average=Avg("rating"), count=Count("id"))
    count = figures["count"] or 0
    average = (
        Decimal(str(figures["average"])).quantize(RATING_STEP, rounding=ROUND_HALF_UP)
        if count
        else None
    )
    MenuItem.objects.filter(pk=menu_item_id).update(average_rating=average, review_count=count)


def _reviewable_line(user: Any, order_line_id: Any) -> OrderItem:
    line = (
        OrderItem.objects.select_related("order", "menu_item")
        .filter(public_id=order_line_id, order__user=user)
        .first()
    )
    if line is None:
        # Someone else's order line is indistinguishable from a missing one.
        raise Http404
    # Delivery, not status: an order refunded after it arrived was still eaten,
    # and one cancelled and refunded before it left never was.
    if line.order.delivered_at is None:
        raise ReviewNotAllowed("You can review a dish once your order has been delivered.")
    if line.menu_item_id is None:
        raise ReviewNotAllowed("This dish is no longer on the menu.")
    return line


@transaction.atomic
def create_review(
    *,
    user: Any,
    order_line_id: Any,
    rating: int,
    title: str,
    comment: str,
    recommends: bool = True,
) -> Review:
    line = _reviewable_line(user, order_line_id)
    if Review.objects.filter(user=user, order_item=line).exists():
        raise AlreadyReviewed()
    try:
        with transaction.atomic():
            return Review.objects.create(
                user=user,
                menu_item=line.menu_item,
                order=line.order,
                order_item=line,
                rating=rating,
                title=title,
                comment=comment,
                recommends=recommends,
                is_verified_purchase=True,
            )
    except IntegrityError as exc:  # a double-submit that raced the check above
        raise AlreadyReviewed() from exc


@transaction.atomic
def update_review(review: Review, **changes: Any) -> Review:
    """Edit within the window. An edited review goes back to moderation.

    Otherwise an approved review could be rewritten into anything after a
    manager had read it.
    """
    if not can_edit(review):
        raise EditWindowClosed(
            f"Reviews can be edited for {settings.REVIEW_EDIT_WINDOW_DAYS} days after posting."
        )
    was_approved = review.status == ReviewStatus.APPROVED
    for field in ("rating", "title", "comment", "recommends"):
        if field in changes:
            setattr(review, field, changes[field])
    review.status = ReviewStatus.PENDING
    review.moderated_by = None
    review.moderated_at = None
    review.rejection_reason = ""
    review.save()
    if was_approved:
        recompute_item_rating(review.menu_item_id)
    return review


@transaction.atomic
def delete_review(review: Review) -> None:
    """Customers may take down their own review at any time."""
    was_approved = review.status == ReviewStatus.APPROVED
    menu_item_id = review.menu_item_id
    review.delete()
    if was_approved:
        recompute_item_rating(menu_item_id)


@transaction.atomic
def moderate(review: Review, *, moderator: Any, approve: bool, reason: str = "") -> Review:
    """Publish or withhold a review. Can be reversed later — an approved review
    that turns out to be abusive can still be taken down."""
    review.status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
    review.rejection_reason = "" if approve else reason.strip()
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.save(
        update_fields=["status", "rejection_reason", "moderated_by", "moderated_at", "updated_at"]
    )
    recompute_item_rating(review.menu_item_id)
    return review


@transaction.atomic
def mark_helpful(review: Review, *, voter_key: str, user: Any = None) -> tuple[int, bool]:
    """Count one vote per voter. Returns the new count and whether this vote was new."""
    if review.status != ReviewStatus.APPROVED:
        raise Http404
    if user is not None and review.user_id == user.pk:
        raise OwnReview()
    _, created = ReviewHelpfulVote.objects.get_or_create(
        review=review, voter_key=voter_key, defaults={"user": user}
    )
    if created:
        Review.objects.filter(pk=review.pk).update(helpful_count=F("helpful_count") + 1)
        review.refresh_from_db(fields=["helpful_count"])
    return review.helpful_count, created


def erase_reviews(user: Any) -> int:
    """Delete a person's reviews on erasure, and correct the ratings they fed."""
    reviews = Review.objects.filter(user=user)
    affected = set(
        reviews.filter(status=ReviewStatus.APPROVED).values_list("menu_item_id", flat=True)
    )
    deleted, _ = reviews.delete()
    for menu_item_id in affected:
        recompute_item_rating(menu_item_id)
    return deleted
