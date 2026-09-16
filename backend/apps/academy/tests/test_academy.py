"""Academy: courses, cohorts with real capacity, paid enrolments, certificates.

Replaces a COURSES array with invented ratings and student counts, a free-text
start date, an unbacked "installment" option, and an enrolment form that ended
in alert("Enrollment submitted successfully!").
"""

from __future__ import annotations

import datetime as dt
import logging

import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from apps.academy import services
from apps.academy.models import (
    Cohort,
    CohortStatus,
    Course,
    Enrolment,
    EnrolmentPaymentMethod,
    EnrolmentStatus,
    ExperienceLevel,
    Instructor,
)
from apps.academy.seed import COURSES, seed_academy
from apps.accounts.models import User
from apps.common.exceptions import PriceChanged
from apps.notifications.models import Notification
from apps.payments.models import PaymentTransaction, TransactionStatus
from apps.payments.services.payments import initialise_enrolment_payment, verify_by_reference

pytestmark = pytest.mark.django_db

COURSES_URL = reverse("v1:academy:courses")
ENROL_URL = reverse("v1:academy:enrol")
MINE_URL = reverse("v1:academy:my-enrolments")


@pytest.fixture(autouse=True)
def simulated_payments(settings):  # type: ignore[no-untyped-def]
    """No provider keys in tests: DEBUG lets the simulated provider stand in."""
    settings.DEBUG = True


@pytest.fixture
def instructor(db) -> Instructor:  # type: ignore[no-untyped-def]
    return Instructor.objects.create(
        name="Chef Emmanuel", bio="Twenty years at the pass.", specialities=["Soups"]
    )


@pytest.fixture
def course(branch, instructor) -> Course:  # type: ignore[no-untyped-def]
    return Course.objects.create(
        branch=branch,
        title="Nigerian Cuisine Fundamentals",
        slug="nigerian-cuisine-fundamentals",
        description="Master the basics",
        instructor=instructor,
        level="beginner",
        course_type="cooking",
        duration_label="4 weeks",
        session_count=8,
        price=5_000_000,
        features=["Recipe Book", "Certificate"],
    )


def in_days(days: int) -> dt.date:
    return timezone.localdate() + dt.timedelta(days=days)


@pytest.fixture
def cohort(course) -> Cohort:  # type: ignore[no-untyped-def]
    return Cohort.objects.create(
        course=course,
        starts_on=in_days(14),
        ends_on=in_days(42),
        capacity=2,
        schedule_note="Saturdays, 10:00–14:00",
    )


@pytest.fixture
def bank(branch):  # type: ignore[no-untyped-def]
    branch.bank_name = "Zenith Bank"
    branch.bank_account_name = "Kuyash Place Ltd"
    branch.bank_account_number = "1012345678"
    branch.save()
    return branch


def enrol(
    cohort: Cohort, email: str = "ada@example.com", method: str = "card", **extra
) -> Enrolment:  # type: ignore[no-untyped-def]
    return services.enrol(
        cohort_id=cohort.pk,
        name=extra.pop("name", "Ada Obi"),
        email=email,
        phone="+2348012345678",
        experience_level="beginner",
        payment_method=method,
        **extra,
    )


def pay(enrolment: Enrolment) -> Enrolment:
    record = initialise_enrolment_payment(enrolment=enrolment)
    verify_by_reference(record.our_reference)
    enrolment.refresh_from_db()
    return enrolment


def templates() -> list[str]:
    return list(Notification.objects.values_list("template_key", flat=True))


# ──────────────────────────────────────────────────────────────────────────────
# Seats and holds (ACA-3, ACA-4)
# ──────────────────────────────────────────────────────────────────────────────


def test_enrolling_holds_a_seat_at_todays_fee(cohort) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort, email="  ADA@Example.com ")
    assert enrolment.status == EnrolmentStatus.PENDING_PAYMENT
    assert enrolment.amount == 5_000_000
    assert enrolment.email == "ada@example.com"
    assert enrolment.reference.startswith("ACA-")
    remaining = enrolment.hold_expires_at - timezone.now()
    assert dt.timedelta(minutes=29) < remaining <= dt.timedelta(minutes=30)
    assert services.seats_left(cohort) == 1


def test_the_last_seat_cannot_be_taken_twice(cohort) -> None:  # type: ignore[no-untyped-def]
    enrol(cohort, "one@example.com")
    enrol(cohort, "two@example.com")
    with pytest.raises(services.CohortFull):
        enrol(cohort, "three@example.com")


def test_a_lapsed_hold_frees_its_seat(cohort) -> None:  # type: ignore[no-untyped-def]
    first = enrol(cohort, "one@example.com")
    enrol(cohort, "two@example.com")
    Enrolment.objects.filter(pk=first.pk).update(
        hold_expires_at=timezone.now() - dt.timedelta(minutes=1)
    )
    assert enrol(cohort, "three@example.com").status == EnrolmentStatus.PENDING_PAYMENT


@pytest.mark.parametrize(
    "change",
    [{"status": CohortStatus.CANCELLED}, {"status": CohortStatus.RUNNING}, {"starts_on": "today"}],
)
def test_classes_that_are_not_open_refuse_enrolment(cohort, change) -> None:  # type: ignore[no-untyped-def]
    if change.get("starts_on") == "today":
        change = {"starts_on": timezone.localdate()}
    Cohort.objects.filter(pk=cohort.pk).update(**change)
    with pytest.raises(services.CohortUnavailable):
        enrol(cohort)


def test_an_unpublished_course_is_not_found(cohort, course) -> None:  # type: ignore[no-untyped-def]
    Course.objects.filter(pk=course.pk).update(is_active=False)
    with pytest.raises(Http404):
        enrol(cohort)


def test_the_same_person_cannot_hold_two_seats(cohort) -> None:  # type: ignore[no-untyped-def]
    first = enrol(cohort)
    with pytest.raises(services.AlreadyEnrolled):
        enrol(cohort, email="Ada@Example.com")
    Enrolment.objects.filter(pk=first.pk).update(
        hold_expires_at=timezone.now() - dt.timedelta(minutes=1)
    )
    enrol(cohort)  # a lapsed hold does not block trying again


def test_a_changed_fee_is_refused(cohort) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PriceChanged) as caught:
        enrol(cohort, expected_amount=4_000_000)
    assert caught.value.extra["price"]["amount"] == 5_000_000
    assert enrol(cohort, expected_amount=5_000_000).amount == 5_000_000


def test_transfer_needs_bank_details(cohort) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(services.TransferUnavailable):
        enrol(cohort, method="transfer")


def test_transfer_holds_longer_and_emails_the_details(cohort, bank) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort, method="transfer")
    assert enrolment.hold_expires_at - timezone.now() > dt.timedelta(hours=47)
    assert templates() == ["enrolment_transfer_details"]
    body = Notification.objects.get().body
    assert "1012345678" in body and enrolment.reference in body and "₦50,000.00" in body


# ──────────────────────────────────────────────────────────────────────────────
# Payment through the shared payment system (ACA-5, ACA-7)
# ──────────────────────────────────────────────────────────────────────────────


def test_card_payment_uses_the_order_payment_system(cohort, settings) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort)
    record = initialise_enrolment_payment(enrolment=enrolment)
    assert record.enrolment == enrolment
    assert record.order is None
    assert record.amount == 5_000_000
    assert record.authorization_url.startswith(settings.ACADEMY_PAYMENT_CALLBACK_URL)

    verify_by_reference(record.our_reference)
    enrolment.refresh_from_db()
    record.refresh_from_db()
    assert record.status == TransactionStatus.SUCCESS
    assert enrolment.status == EnrolmentStatus.CONFIRMED
    assert enrolment.amount_paid == 5_000_000
    assert enrolment.hold_expires_at is None
    cohort.refresh_from_db()
    assert cohort.enrolled_count == 1
    assert "enrolment_confirmed" in templates()
    email = Notification.objects.get(template_key="enrolment_confirmed")
    assert "Saturdays, 10:00–14:00" in email.body
    assert f"/academy/enrolments/{enrolment.reference}?token={enrolment.guest_token}" in email.body


def test_confirmation_is_idempotent(cohort) -> None:  # type: ignore[no-untyped-def]
    enrolment = pay(enrol(cohort))
    record = PaymentTransaction.objects.get(enrolment=enrolment)
    services.confirm_payment(enrolment, record)
    assert Notification.objects.filter(template_key="enrolment_confirmed").count() == 1


def test_account_holders_get_a_plain_link(cohort, verified_user) -> None:  # type: ignore[no-untyped-def]
    enrolment = pay(enrol(cohort, user=verified_user))
    assert services.manage_url(enrolment).endswith(f"/academy/enrolments/{enrolment.reference}")


def test_only_live_card_enrolments_can_be_paid(cohort, bank) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(services.EnrolmentNotPayable):
        initialise_enrolment_payment(enrolment=enrol(cohort, method="transfer"))
    lapsed = enrol(cohort, "two@example.com")
    Enrolment.objects.filter(pk=lapsed.pk).update(
        hold_expires_at=timezone.now() - dt.timedelta(seconds=1)
    )
    lapsed.refresh_from_db()
    with pytest.raises(services.EnrolmentExpired):
        initialise_enrolment_payment(enrolment=lapsed)


def test_a_full_cohort_is_marked_full_and_reopens_on_cancellation(cohort) -> None:  # type: ignore[no-untyped-def]
    first = pay(enrol(cohort, "one@example.com"))
    pay(enrol(cohort, "two@example.com"))
    cohort.refresh_from_db()
    assert cohort.status == CohortStatus.FULL
    assert cohort.enrolled_count == 2

    services.cancel_enrolment(enrolment=first, reason="Moved abroad")
    cohort.refresh_from_db()
    assert cohort.status == CohortStatus.OPEN
    assert cohort.enrolled_count == 1
    with pytest.raises(services.EnrolmentStateError):
        services.cancel_enrolment(enrolment=first)


def test_a_payment_after_cancellation_is_kept_and_flagged(cohort, caplog) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort)
    record = initialise_enrolment_payment(enrolment=enrolment)
    services.cancel_enrolment(enrolment=enrolment)
    with caplog.at_level(logging.CRITICAL):
        verify_by_reference(record.our_reference)
    enrolment.refresh_from_db()
    assert enrolment.status == EnrolmentStatus.CANCELLED
    assert enrolment.amount_paid == 5_000_000
    assert "payment_for_cancelled_enrolment" in caplog.text


def test_a_late_payment_into_a_filled_cohort_is_not_confirmed(cohort, caplog) -> None:  # type: ignore[no-untyped-def]
    """The hold lapsed and the seat went to someone else.

    Confirming anyway sold one seat twice, and the student found out by turning
    up to a class with no place for them. The fee is recorded and flagged
    instead, and a person decides between a refund and another place.
    """
    late = enrol(cohort, "late@example.com")
    record = initialise_enrolment_payment(enrolment=late)
    Enrolment.objects.filter(pk=late.pk).update(
        hold_expires_at=timezone.now() - dt.timedelta(minutes=1)
    )
    pay(enrol(cohort, "one@example.com"))
    pay(enrol(cohort, "two@example.com"))

    with caplog.at_level(logging.CRITICAL):
        verify_by_reference(record.our_reference)

    late.refresh_from_db()
    record.refresh_from_db()
    cohort.refresh_from_db()
    assert late.status == EnrolmentStatus.PENDING_PAYMENT  # not confirmed
    assert late.paid_at is not None and late.amount_paid == 5_000_000  # but the money is kept
    assert cohort.enrolled_count == 2  # and the cohort is not overbooked
    assert record.needs_review is True
    assert "refund or seat decision needed" in record.review_reason
    assert "payment_for_unavailable_seat" in caplog.text
    # The two students who did get seats are confirmed; this one is not told
    # they have a place, because they do not have one.
    assert not Notification.objects.filter(
        template_key="enrolment_confirmed", body__contains=late.reference
    ).exists()


def test_staff_record_a_transfer(cohort, bank) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort, method="transfer")
    services.record_transfer(enrolment=enrolment)
    enrolment.refresh_from_db()
    assert enrolment.status == EnrolmentStatus.CONFIRMED
    assert PaymentTransaction.objects.get(enrolment=enrolment).provider == "bank_transfer"
    with pytest.raises(services.EnrolmentStateError):
        services.record_transfer(enrolment=enrolment)


def test_a_transaction_pays_for_exactly_one_thing(cohort, ready_cart) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.services.placement import place_order

    order = place_order(cart=ready_cart, payment_method="card")
    enrolment = enrol(cohort)
    for links in ({}, {"order": order, "enrolment": enrolment}):
        with pytest.raises(IntegrityError), transaction.atomic():
            PaymentTransaction.objects.create(
                provider="paystack", our_reference=f"x-{len(links)}", amount=1, **links
            )
    assert PaymentTransaction.objects.filter(enrolment=enrolment).count() == 0


# ──────────────────────────────────────────────────────────────────────────────
# Completion and certificates
# ──────────────────────────────────────────────────────────────────────────────


def test_completion_issues_a_certificate(cohort) -> None:  # type: ignore[no-untyped-def]
    enrolment = pay(enrol(cohort))
    with pytest.raises(services.CertificateNotAvailable):
        services.certificate_pdf(enrolment)

    services.complete_enrolment(enrolment=enrolment)
    enrolment.refresh_from_db()
    assert enrolment.status == EnrolmentStatus.COMPLETED
    assert enrolment.certificate_issued_at is not None
    assert "enrolment_certificate" in templates()
    assert services.certificate_pdf(enrolment).startswith(b"%PDF")
    with pytest.raises(services.EnrolmentStateError):
        services.complete_enrolment(enrolment=enrolment)


def test_unpaid_enrolments_cannot_be_completed(cohort) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(services.EnrolmentStateError):
        services.complete_enrolment(enrolment=enrol(cohort))


def test_labels(cohort, instructor, course) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort)
    assert str(instructor) == "Chef Emmanuel"
    assert str(course) == course.title
    assert str(cohort).startswith(course.title)
    assert str(enrolment) == f"{enrolment.reference} — Ada Obi"


# ──────────────────────────────────────────────────────────────────────────────
# Catalogue API
# ──────────────────────────────────────────────────────────────────────────────


def test_course_list_counts_students_and_shows_the_next_class(
    api_client, cohort, course, instructor
) -> None:  # type: ignore[no-untyped-def]
    pay(enrol(cohort, "one@example.com"))
    enrol(cohort, "held@example.com")  # held, not paid: not a student
    Course.objects.create(
        branch=course.branch,
        title="Draft",
        slug="draft",
        description="d",
        instructor=instructor,
        level="advanced",
        course_type="baking",
        duration_label="1 week",
        session_count=1,
        price=1,
        is_active=False,
    )

    body = api_client.get(COURSES_URL).json()
    assert [row["slug"] for row in body] == [course.slug]
    row = body[0]
    assert row["price"]["display"] == "₦50,000.00"
    assert row["student_count"] == 1
    assert row["type"] == "cooking" and row["type_display"] == "Cooking"
    assert row["instructor"] == {"name": "Chef Emmanuel", "photo_url": None}
    assert row["next_cohort"]["id"] == str(cohort.pk)
    assert row["next_cohort"]["seats_left"] == 0
    assert "rating" not in row


def test_next_class_prefers_one_with_seats(api_client, cohort, course) -> None:  # type: ignore[no-untyped-def]
    later = Cohort.objects.create(
        course=course, starts_on=in_days(60), ends_on=in_days(90), capacity=10
    )
    pay(enrol(cohort, "one@example.com"))
    pay(enrol(cohort, "two@example.com"))
    assert api_client.get(COURSES_URL).json()[0]["next_cohort"]["id"] == str(later.pk)


def test_courses_without_classes_have_no_next_class(api_client, course) -> None:  # type: ignore[no-untyped-def]
    Cohort.objects.create(
        course=course, starts_on=in_days(-30), ends_on=in_days(-2), capacity=5, status="completed"
    )
    assert api_client.get(COURSES_URL).json()[0]["next_cohort"] is None


def test_course_filters(api_client, course, instructor) -> None:  # type: ignore[no-untyped-def]
    Course.objects.create(
        branch=course.branch,
        title="Pastry",
        slug="pastry",
        description="Breads",
        instructor=instructor,
        level="advanced",
        course_type="baking",
        duration_label="6 weeks",
        session_count=12,
        price=7_500_000,
    )

    def slugs(**params):  # type: ignore[no-untyped-def]
        return sorted(row["slug"] for row in api_client.get(COURSES_URL, params).json())

    assert slugs(level="advanced") == ["pastry"]
    assert slugs(type="cooking") == [course.slug]
    assert slugs(search="bread") == ["pastry"]
    assert slugs(search="emmanuel") == sorted([course.slug, "pastry"])
    bad = api_client.get(COURSES_URL, {"type": "karate"})
    assert bad.status_code == 400 and "type" in bad.json()["errors"]


def test_course_detail_and_cohorts(api_client, cohort, course) -> None:  # type: ignore[no-untyped-def]
    detail = api_client.get(
        reverse("v1:academy:course-detail", kwargs={"slug": course.slug})
    ).json()
    assert detail["instructor"]["bio"] == "Twenty years at the pass."
    assert [c["id"] for c in detail["cohorts"]] == [str(cohort.pk)]
    assert detail["cohorts"][0]["seats_left"] == 2

    cohorts = api_client.get(
        reverse("v1:academy:course-cohorts", kwargs={"slug": course.slug})
    ).json()
    assert cohorts[0]["schedule_note"] == "Saturdays, 10:00–14:00"
    assert (
        api_client.get(reverse("v1:academy:course-detail", kwargs={"slug": "nope"})).status_code
        == 404
    )


def test_detail_without_prefetch_falls_back(cohort, course) -> None:  # type: ignore[no-untyped-def]
    from apps.academy.serializers import CourseDetailSerializer

    data = CourseDetailSerializer(course).data
    assert [c["id"] for c in data["cohorts"]] == [str(cohort.pk)]
    assert data["student_count"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Enrolment API
# ──────────────────────────────────────────────────────────────────────────────


def payload(cohort: Cohort, **extra) -> dict:  # type: ignore[no-untyped-def]
    return {
        "cohort": str(cohort.pk),
        "name": "Ada Obi",
        "email": "ada@example.com",
        "phone": "+2348012345678",
        "experience_level": "beginner",
        "payment_method": "card",
        "expected_amount": 5_000_000,
        **extra,
    }


def test_enrolment_needs_an_idempotency_key(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(ENROL_URL, payload(cohort), format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


def test_guest_card_enrolment(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k1")
    assert response.status_code == 201, response.json()
    body = response.json()
    reference = body["enrolment"]["reference"]
    assert body["payment"]["authorization_url"]
    assert body["payment_error"] == ""
    assert body["enrolment"]["can_pay"] is True
    assert body["enrolment"]["cohort"]["seats_left"] == 1
    token = body["guest_token"]

    replay = api_client.post(ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k1")
    assert replay["Idempotency-Replayed"] == "true"
    assert Enrolment.objects.count() == 1

    detail_url = reverse("v1:academy:enrolment", kwargs={"reference": reference})
    assert api_client.get(detail_url).status_code == 404
    assert api_client.get(detail_url, HTTP_X_ENROLMENT_TOKEN="wrong").status_code == 404
    assert (
        api_client.get(detail_url, HTTP_X_ENROLMENT_TOKEN=token).json()["status"]
        == "pending_payment"
    )

    verify = api_client.get(
        reverse("v1:academy:payment-verify", kwargs={"reference": body["payment"]["reference"]})
    )
    assert verify.json() == {
        "status": "success",
        "enrolment_reference": reference,
        "enrolment_status": "confirmed",
    }
    # The order verification endpoint does not answer for course payments.
    order_verify = reverse("v1:payments:verify", kwargs={"reference": body["payment"]["reference"]})
    assert api_client.get(order_verify).status_code == 404


def test_signed_in_enrolment_needs_no_token(api_client, cohort, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    body = api_client.post(
        ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k2"
    ).json()
    assert "guest_token" not in body
    assert [row["reference"] for row in api_client.get(MINE_URL).json()] == [
        body["enrolment"]["reference"]
    ]
    detail_url = reverse(
        "v1:academy:enrolment", kwargs={"reference": body["enrolment"]["reference"]}
    )
    assert api_client.get(detail_url).status_code == 200


def test_managers_can_read_any_enrolment(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort)
    manager = User.objects.create_user(email="mgr@example.com", password="x" * 16)
    manager.groups.add(Group.objects.get_or_create(name="managers")[0])
    api_client.force_authenticate(manager)
    assert (
        api_client.get(
            reverse("v1:academy:enrolment", kwargs={"reference": enrolment.reference})
        ).status_code
        == 200
    )


def test_transfer_enrolment_returns_bank_details(api_client, cohort, bank) -> None:  # type: ignore[no-untyped-def]
    body = api_client.post(
        ENROL_URL,
        payload(cohort, payment_method="transfer"),
        format="json",
        HTTP_IDEMPOTENCY_KEY="k3",
    ).json()
    assert body["payment"] is None
    assert body["enrolment"]["bank_transfer"] == {
        "bank_name": "Zenith Bank",
        "account_name": "Kuyash Place Ltd",
        "account_number": "1012345678",
    }
    assert body["enrolment"]["can_pay"] is False


def test_enrolment_conflicts_have_stable_codes(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    enrol(cohort, "one@example.com")
    enrol(cohort, "two@example.com")
    response = api_client.post(ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k4")
    assert response.status_code == 409
    assert response.json()["code"] == "cohort_full"
    # The failed attempt released its idempotency claim.
    again = api_client.post(ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k4")
    assert again.json()["code"] == "cohort_full"


def test_a_failed_payment_start_still_saves_the_enrolment(api_client, cohort, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from apps.common.exceptions import PaymentFailed
    from apps.payments.services import payments

    def boom(**kwargs):  # type: ignore[no-untyped-def]
        raise PaymentFailed("No payment provider is available right now.")

    monkeypatch.setattr(payments, "initialise_enrolment_payment", boom)
    body = api_client.post(
        ENROL_URL, payload(cohort), format="json", HTTP_IDEMPOTENCY_KEY="k5"
    ).json()
    assert body["payment"] is None
    assert body["payment_error"] == "No payment provider is available right now."
    monkeypatch.undo()

    token = body["guest_token"]
    pay_url = reverse(
        "v1:academy:enrolment-pay", kwargs={"reference": body["enrolment"]["reference"]}
    )
    retry = api_client.post(pay_url, HTTP_X_ENROLMENT_TOKEN=token)
    assert retry.status_code == 201
    assert retry.json()["authorization_url"]


def test_certificate_download(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    enrolment = pay(enrol(cohort))
    url = reverse("v1:academy:enrolment-certificate", kwargs={"reference": enrolment.reference})
    early = api_client.get(url, HTTP_X_ENROLMENT_TOKEN=enrolment.guest_token)
    assert early.status_code == 409 and early.json()["code"] == "certificate_not_available"

    services.complete_enrolment(enrolment=enrolment)
    response = api_client.get(url, HTTP_X_ENROLMENT_TOKEN=enrolment.guest_token)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert enrolment.reference in response["Content-Disposition"]


def test_verify_unknown_reference(api_client) -> None:  # type: ignore[no-untyped-def]
    assert (
        api_client.get(
            reverse("v1:academy:payment-verify", kwargs={"reference": "nope"})
        ).status_code
        == 404
    )


def test_order_payments_are_untouched(api_client, ready_cart, verified_user) -> None:  # type: ignore[no-untyped-def]
    from apps.orders.services.placement import place_order
    from apps.payments.services.payments import initialise_payment

    order = place_order(cart=ready_cart, payment_method="card")
    record = initialise_payment(order=order)
    assert record.enrolment is None

    # The order endpoint gates on ownership, so the customer signs in for it.
    api_client.force_authenticate(verified_user)
    verify = api_client.get(
        reverse("v1:payments:verify", kwargs={"reference": record.our_reference})
    ).json()
    assert verify["order_status"] == "paid"


def test_the_course_list_does_not_query_once_per_cohort(api_client, course, cohort) -> None:  # type: ignore[no-untyped-def]
    """``seats_left`` cost a COUNT(*) per cohort, on a list with no pagination.

    Measured at +3 queries per course. Seats are annotated onto the prefetched
    cohorts now, so the count is flat however many classes are scheduled.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def queries() -> int:
        with CaptureQueriesContext(connection) as captured:
            api_client.get(COURSES_URL)
        return len(captured)

    queries()  # warm anything cached on first use
    baseline = queries()

    for offset in (20, 30, 40):
        Cohort.objects.create(
            course=course, starts_on=in_days(offset), ends_on=in_days(offset + 20), capacity=5
        )

    assert queries() == baseline


def test_an_enrolment_token_is_accepted_only_as_a_header(api_client, cohort) -> None:  # type: ignore[no-untyped-def]
    """Tokens must not travel in URLs (SECURITY.md §7.5).

    The emailed link still carries one — customers already have those links, and
    the frontend lifts it into storage and strips it from the address bar — but
    the API itself reads the token from a header and nowhere else, so a copied
    URL in a log, a Referer header or a shared screenshot is not a credential
    the API will accept.
    """
    enrolment = enrol(cohort)
    url = reverse("v1:academy:enrolment", kwargs={"reference": enrolment.reference})

    assert api_client.get(url, {"token": enrolment.guest_token}).status_code == 404
    assert api_client.get(url, HTTP_X_ENROLMENT_TOKEN=enrolment.guest_token).status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Admin and seed
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client_logged_in(client, db):  # type: ignore[no-untyped-def]
    client.force_login(User.objects.create_superuser(email="root@example.com", password="x" * 16))
    return client


def run_action(client, action: str, enrolment: Enrolment):  # type: ignore[no-untyped-def]
    return client.post(
        reverse("admin:academy_enrolment_changelist"),
        {"action": action, "_selected_action": [str(enrolment.pk)]},
        follow=True,
    )


def test_admin_actions(admin_client_logged_in, cohort, bank) -> None:  # type: ignore[no-untyped-def]
    enrolment = enrol(cohort, method="transfer")
    page = run_action(admin_client_logged_in, "record_transfer", enrolment)
    assert "Confirmed 1 enrolment" in page.content.decode()

    page = run_action(admin_client_logged_in, "record_transfer", enrolment)
    assert "Only an unpaid enrolment" in page.content.decode()

    run_action(admin_client_logged_in, "complete_and_certify", enrolment)
    enrolment.refresh_from_db()
    assert enrolment.status == EnrolmentStatus.COMPLETED

    other = enrol(cohort, "two@example.com")
    run_action(admin_client_logged_in, "cancel", other)
    other.refresh_from_db()
    assert other.status == EnrolmentStatus.CANCELLED


def test_admin_pages_render(admin_client_logged_in, cohort, course) -> None:  # type: ignore[no-untyped-def]
    enrol(cohort)
    for name in (
        "admin:academy_course_changelist",
        "admin:academy_enrolment_changelist",
        "admin:academy_instructor_changelist",
    ):
        assert admin_client_logged_in.get(reverse(name)).status_code == 200
    change = admin_client_logged_in.get(reverse("admin:academy_course_change", args=[course.pk]))
    assert change.status_code == 200
    assert "Seats left" in change.content.decode()
    add = admin_client_logged_in.get(reverse("admin:academy_course_add"))
    assert add.context["adminform"].form.initial["branch"] == str(course.branch.pk)


def test_seed_is_inactive_and_idempotent(branch) -> None:  # type: ignore[no-untyped-def]
    import io

    out = io.StringIO()
    assert seed_academy(branch, stdout=out) == len(COURSES)
    assert "inactive until reviewed" in out.getvalue()
    assert seed_academy(branch) == 0
    assert not Course.objects.filter(is_active=True).exists()
    assert Course.objects.get(slug="culinary-masterclass").price == 15_000_000


def test_a_cohort_past_capacity_is_reported_critically(cohort, caplog) -> None:  # type: ignore[no-untyped-def]
    """A payment settling after its hold lapsed can oversell a seat.

    The count is authoritative, so the enrolment stands and a person must sort
    it out — but it must never pass silently.
    """
    cohort.capacity = 1
    cohort.save(update_fields=["capacity"])
    for index in range(2):
        Enrolment.objects.create(
            course=cohort.course,
            cohort=cohort,
            name=f"Student {index}",
            email=f"student-{index}@example.com",
            phone="+2348012345678",
            experience_level=ExperienceLevel.values[0],
            payment_method=EnrolmentPaymentMethod.values[0],
            status=EnrolmentStatus.CONFIRMED,
            amount=cohort.course.price,
        )

    with caplog.at_level(logging.CRITICAL, logger="apps.academy.services"):
        services._refresh_cohort(cohort)

    [record] = [r for r in caplog.records if r.getMessage() == "cohort_overbooked"]
    assert record.enrolled == 2 and record.capacity == 1  # type: ignore[attr-defined]


def _keyed_enrolment(cohort, key: str) -> Enrolment:
    return Enrolment.objects.create(
        course=cohort.course,
        cohort=cohort,
        name="Student",
        email="student@example.com",
        phone="+2348012345678",
        experience_level=ExperienceLevel.values[0],
        payment_method=EnrolmentPaymentMethod.values[0],
        status=EnrolmentStatus.PENDING_PAYMENT,
        amount=cohort.course.price,
        idempotency_key=key,
    )


def test_two_enrolments_cannot_share_an_idempotency_key(cohort) -> None:  # type: ignore[no-untyped-def]
    _keyed_enrolment(cohort, "enrol-abc")
    with pytest.raises(IntegrityError), transaction.atomic():
        _keyed_enrolment(cohort, "enrol-abc")


def test_blank_enrolment_keys_do_not_collide(cohort) -> None:  # type: ignore[no-untyped-def]
    _keyed_enrolment(cohort, "")
    _keyed_enrolment(cohort, "")
    assert Enrolment.objects.filter(idempotency_key="").count() == 2
