"""Catering enquiries.

Gate 2 requires that every enquiry reaches a human with an SLA timer. The
current form answers a potential ₦6M booking with `console.log`.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catering.models import CateringEnquiry, CateringPackage, EnquiryStatus
from apps.catering.services import (
    EnquiryRejected,
    overdue_enquiries,
    record_response,
    submit_enquiry,
)
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def packages(db, branch):  # type: ignore[no-untyped-def]
    from apps.catering.seed import seed_catering

    seed_catering(branch)
    return {p.slug: p for p in CateringPackage.objects.all()}


def enquire(branch, packages=None, **overrides):  # type: ignore[no-untyped-def]
    payload = {
        "branch": branch,
        "name": "Ada Obi",
        "email": "ada@example.com",
        "phone": "+2348012345678",
        "guest_count": 50,
        "event_type": "Wedding",
        "venue": "Eko Hotel",
        **overrides,
    }
    return submit_enquiry(**payload)


# ── Persistence, the thing that is missing today ──────────────────────────────


def test_an_enquiry_is_recorded(branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch, package=packages["premium"])

    assert CateringEnquiry.objects.count() == 1
    assert enquiry.reference.startswith("CAT-")
    assert enquiry.status == EnquiryStatus.NEW
    assert enquiry.guest_count == 50
    assert enquiry.venue == "Eko Hotel"


def test_the_indicative_total_is_computed_server_side(branch, packages) -> None:  # type: ignore[no-untyped-def]
    """50 guests × ₦6,500 = ₦325,000. Never taken from the client."""
    enquiry = enquire(branch, package=packages["premium"], guest_count=50)
    assert enquiry.indicative_total == 50 * 650_000


def test_no_package_means_no_indicative_total(branch, packages) -> None:  # type: ignore[no-untyped-def]
    assert enquire(branch).indicative_total == 0


def test_the_customer_is_acknowledged_with_a_deadline(branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch, package=packages["premium"])
    email = Notification.objects.get(template_key="catering_enquiry_received")

    assert email.recipient == "ada@example.com"
    assert enquiry.reference in email.body
    assert "₦325,000.00" in email.body


def test_the_team_is_alerted(branch, packages) -> None:  # type: ignore[no-untyped-def]
    """Gate 2: the enquiry must reach a human, not just a table."""
    enquiry = enquire(branch, package=packages["premium"])
    alert = Notification.objects.get(template_key="catering_enquiry_internal")

    assert enquiry.reference in alert.subject
    assert "ada@example.com" in alert.body
    assert "Eko Hotel" in alert.body


def test_a_luxury_enquiry_is_captured_in_full(branch, packages) -> None:  # type: ignore[no-untyped-def]
    """The case the current form loses: 300 guests at ₦12,000 a head."""
    enquiry = enquire(branch, package=packages["luxury"], guest_count=300)
    assert enquiry.indicative_total == 300 * 1_200_000  # ₦3,600,000.00
    assert CateringEnquiry.objects.filter(reference=enquiry.reference).exists()


# ── Validation ────────────────────────────────────────────────────────────────


def test_a_package_that_does_not_fit_the_party_is_refused(branch, packages) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(EnquiryRejected, match="10–30 guests"):
        enquire(branch, package=packages["essential"], guest_count=200)


def test_a_past_event_date_is_refused(branch, packages) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(EnquiryRejected, match="already passed"):
        enquire(branch, event_date=timezone.localdate() - dt.timedelta(days=1))


def test_a_zero_guest_enquiry_is_refused(branch, packages) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(EnquiryRejected, match="how many guests"):
        enquire(branch, guest_count=0)


# ── The SLA clock ─────────────────────────────────────────────────────────────


def test_a_new_enquiry_is_not_overdue(branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    assert enquiry.is_overdue is False
    assert 23 < enquiry.hours_remaining <= 24


def test_an_unanswered_enquiry_goes_overdue_after_24_hours(branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    CateringEnquiry.objects.filter(pk=enquiry.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=30)
    )
    enquiry.refresh_from_db()

    assert enquiry.is_overdue is True
    assert enquiry.hours_remaining < 0
    assert [e.pk for e in overdue_enquiries(branch)] == [enquiry.pk]


def test_answering_stops_the_clock(branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    CateringEnquiry.objects.filter(pk=enquiry.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=30)
    )
    enquiry.refresh_from_db()
    assert enquiry.is_overdue is True

    record_response(enquiry=enquiry, status=EnquiryStatus.CONTACTED)

    enquiry.refresh_from_db()
    assert enquiry.is_overdue is False
    assert enquiry.responded_at is not None
    assert overdue_enquiries(branch) == []


def test_recording_a_response_captures_the_quote_and_owner(branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch, package=packages["premium"])
    record_response(
        enquiry=enquiry,
        status=EnquiryStatus.QUOTED,
        quoted_amount=40_000_000,
        notes="Quoted with live cooking station",
        actor=manager_user,
    )
    enquiry.refresh_from_db()
    assert enquiry.quoted_amount == 40_000_000
    assert enquiry.assigned_to == manager_user
    assert "live cooking station" in enquiry.internal_notes


def test_notes_accumulate_rather_than_overwrite(branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    record_response(enquiry=enquiry, notes="Left voicemail", actor=manager_user)
    record_response(enquiry=enquiry, notes="Spoke to them", actor=manager_user)

    enquiry.refresh_from_db()
    assert "Left voicemail" in enquiry.internal_notes
    assert "Spoke to them" in enquiry.internal_notes


def test_the_first_response_time_is_not_overwritten(branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    """SLA compliance is measured on the first reply, not the latest touch."""
    enquiry = enquire(branch)
    record_response(enquiry=enquiry, actor=manager_user)
    first = CateringEnquiry.objects.get(pk=enquiry.pk).responded_at

    record_response(enquiry=enquiry, status=EnquiryStatus.WON, actor=manager_user)
    assert CateringEnquiry.objects.get(pk=enquiry.pk).responded_at == first


# ── API ───────────────────────────────────────────────────────────────────────


def test_packages_are_listed(api_client, packages) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get(reverse("v1:catering:packages")).json()
    assert [row["slug"] for row in body] == ["essential", "premium", "luxury"]
    assert body[1]["price_per_person"]["display"] == "₦6,500.00"
    assert body[1]["is_popular"] is True


def test_submitting_through_the_api(api_client, packages) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:catering:enquiry-create"),
        {
            "name": "Ada Obi",
            "email": "ada@example.com",
            "phone": "+2348012345678",
            "guest_count": 120,
            "package": "luxury",
            "event_type": "Wedding",
            "venue": "Eko Hotel",
            "message": "Outdoor reception",
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("CAT-")
    assert body["indicative_total"]["display"] == "₦1,440,000.00"
    assert "Indicative only" in body["indicative_note"]
    assert body["respond_by"]


def test_a_client_supplied_total_is_ignored(api_client, packages) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:catering:enquiry-create"),
        {
            "name": "Ada",
            "email": "a@example.com",
            "phone": "+2348012345678",
            "guest_count": 50,
            "package": "premium",
            "indicative_total": 1,
            "quoted_amount": 1,
        },
        format="json",
    )
    assert response.json()["indicative_total"]["amount"] == 50 * 650_000


def test_an_unknown_package_is_treated_as_none(api_client, packages) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:catering:enquiry-create"),
        {
            "name": "Ada",
            "email": "a@example.com",
            "phone": "+2348012345678",
            "guest_count": 50,
            "package": "platinum",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["indicative_total"]["amount"] == 0


def test_a_mismatched_package_returns_422(api_client, packages) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:catering:enquiry-create"),
        {
            "name": "Ada",
            "email": "a@example.com",
            "phone": "+2348012345678",
            "guest_count": 500,
            "package": "essential",
        },
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["code"] == "enquiry_rejected"


def test_an_enquirer_can_check_progress_with_their_email(api_client, branch, packages) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    url = reverse("v1:catering:enquiry-detail", kwargs={"reference": enquiry.reference})

    assert api_client.get(url).status_code == 404
    assert api_client.get(url, {"email": "ada@example.com"}).status_code == 200
    assert api_client.get(url, {"email": "someone@else.com"}).status_code == 404


def test_internal_notes_are_never_exposed(api_client, branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    record_response(
        enquiry=enquiry, notes="Customer haggled hard", quoted_amount=1, actor=manager_user
    )
    body = api_client.get(
        reverse("v1:catering:enquiry-detail", kwargs={"reference": enquiry.reference}),
        {"email": "ada@example.com"},
    ).json()

    assert "internal_notes" not in body
    assert "quoted_amount" not in body


def test_the_overdue_list_requires_a_manager(api_client, branch, packages, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    assert api_client.get(reverse("v1:catering:enquiries-overdue")).status_code in (401, 403)
    api_client.force_authenticate(user=kitchen_user)
    assert api_client.get(reverse("v1:catering:enquiries-overdue")).status_code == 403


def test_the_overdue_list_reports_how_late(api_client, branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    enquiry = enquire(branch)
    CateringEnquiry.objects.filter(pk=enquiry.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=36)
    )

    api_client.force_authenticate(user=manager_user)
    body = api_client.get(reverse("v1:catering:enquiries-overdue")).json()

    assert body["count"] == 1
    assert body["enquiries"][0]["reference"] == enquiry.reference
    assert body["enquiries"][0]["hours_overdue"] >= 11


# ── Admin: the queue a manager actually works from ───────────────────────────


def admin_instance():  # type: ignore[no-untyped-def]
    from django.contrib.admin.sites import AdminSite

    from apps.catering.admin import CateringEnquiryAdmin

    return CateringEnquiryAdmin(CateringEnquiry, AdminSite())


def fake_request(user):  # type: ignore[no-untyped-def]
    from django.test import RequestFactory

    request = RequestFactory().get("/admin/catering/cateringenquiry/")
    request.user = user
    return request


def test_the_admin_sla_column_flags_overdue_work(branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    admin = admin_instance()

    fresh = enquire(branch, email="fresh@example.com")
    assert "left" in admin.sla(fresh)

    late = enquire(branch, email="late@example.com")
    CateringEnquiry.objects.filter(pk=late.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=40)
    )
    late.refresh_from_db()
    assert "overdue" in admin.sla(late)

    record_response(enquiry=late, actor=manager_user)
    late.refresh_from_db()
    assert "answered" in admin.sla(late)


def test_the_admin_actions_stop_the_clock(branch, packages, manager_user) -> None:  # type: ignore[no-untyped-def]
    admin = admin_instance()
    admin.message_user = lambda *args, **kwargs: None  # type: ignore[assignment]
    request = fake_request(manager_user)

    enquiry = enquire(branch)
    queryset = CateringEnquiry.objects.filter(pk=enquiry.pk)

    admin.mark_contacted(request, queryset)
    enquiry.refresh_from_db()
    assert enquiry.status == EnquiryStatus.CONTACTED
    assert enquiry.responded_at is not None

    admin.mark_won(request, queryset)
    enquiry.refresh_from_db()
    assert enquiry.status == EnquiryStatus.WON

    admin.mark_lost(request, queryset)
    enquiry.refresh_from_db()
    assert enquiry.status == EnquiryStatus.LOST


def test_a_package_knows_which_parties_it_suits(branch, packages) -> None:  # type: ignore[no-untyped-def]
    essential = packages["essential"]
    assert essential.suits(10) is True
    assert essential.suits(30) is True
    assert essential.suits(31) is False
    assert essential.indicative_total(20) == 20 * 350_000
    assert essential.indicative_total(-5) == 0
