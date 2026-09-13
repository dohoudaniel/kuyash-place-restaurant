"""Contact form, tickets and the FAQ.

Replaces a form whose submit handler sets a success flag and never lets the
message leave the component.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.notifications.models import Notification
from apps.support.models import ContactMessage, FaqEntry, Ticket, TicketReply, TicketStatus
from apps.support.services import (
    MessageRejected,
    looks_like_spam,
    reply_to_ticket,
    resolve_ticket,
    submit_contact_message,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def site_settings(db):  # type: ignore[no-untyped-def]
    from apps.core.models import SiteSettings

    row = SiteSettings.load()
    row.support_email = "support@kuyashplace.com"
    row.save()
    return row


def send(branch, **overrides):  # type: ignore[no-untyped-def]
    payload = {
        "branch": branch,
        "name": "Ada Obi",
        "email": "ada@example.com",
        "message": "Do you cater for 200 people?",
        "subject": "Catering question",
        **overrides,
    }
    return submit_contact_message(**payload)


# ── The message now survives ──────────────────────────────────────────────────


def test_a_message_opens_a_ticket(branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)

    assert ContactMessage.objects.count() == 1
    assert ticket is not None
    assert ticket.reference.startswith("SUP-")
    assert ticket.status == TicketStatus.OPEN
    assert ticket.replies.count() == 1
    assert ticket.replies.first().body == "Do you cater for 200 people?"


def test_both_parties_are_emailed(branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)

    ack = Notification.objects.get(template_key="contact_received")
    assert ack.recipient == "ada@example.com"
    assert ticket.reference in ack.body

    alert = Notification.objects.get(template_key="contact_internal")
    assert alert.recipient == "support@kuyashplace.com"
    assert "Do you cater for 200 people?" in alert.body


def test_a_signed_in_customer_is_linked(branch, site_settings, verified_user) -> None:  # type: ignore[no-untyped-def]
    assert send(branch, user=verified_user).user == verified_user


def test_an_empty_message_is_refused(branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(MessageRejected, match="how we can help"):
        send(branch, message="   ")


def test_a_missing_subject_gets_a_sensible_one(branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch, subject="", reason="catering")
    assert ticket.subject == "Catering enquiry"


# ── Spam ──────────────────────────────────────────────────────────────────────


def test_the_honeypot_catches_bots() -> None:
    """A field hidden from humans. Only a bot fills it in."""
    assert looks_like_spam(message="hello", honeypot="http://spam.example") is True
    assert looks_like_spam(message="hello", honeypot="") is False


def test_link_flooding_is_caught() -> None:
    assert looks_like_spam(message="https://a " * 8) is True
    assert looks_like_spam(message="See https://kuyashplace.com for the menu") is False


def test_known_spam_phrases_are_caught() -> None:
    assert looks_like_spam(message="cheap SEO services and backlinks") is True


def test_spam_is_quarantined_not_ticketed(branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    result = send(branch, honeypot="gotcha")

    assert result is None
    assert Ticket.objects.count() == 0
    assert ContactMessage.objects.get().is_spam is True
    assert Notification.objects.count() == 0  # nobody is bothered


def test_a_bot_learns_nothing_from_the_response(api_client, branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    """Spam and genuine messages get the same status code and shape."""
    real = api_client.post(
        reverse("v1:support:contact"),
        {"name": "Ada", "email": "a@example.com", "message": "Hello there"},
        format="json",
    )
    spam = api_client.post(
        reverse("v1:support:contact"),
        {"name": "Bot", "email": "b@example.com", "message": "Hi", "website": "x"},
        format="json",
    )
    assert real.status_code == spam.status_code == 201
    assert set(real.json()) == set(spam.json())


# ── Replies ───────────────────────────────────────────────────────────────────


def test_a_staff_reply_emails_the_customer(branch, site_settings, manager_user) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    Notification.objects.all().delete()

    reply_to_ticket(ticket=ticket, body="Yes, we cater for 200.", author=manager_user)

    email = Notification.objects.get(template_key="ticket_reply")
    assert email.recipient == "ada@example.com"
    assert "Yes, we cater for 200." in email.body

    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.PENDING


def test_an_internal_note_is_never_sent_or_shown(  # type: ignore[no-untyped-def]
    api_client, branch, site_settings, manager_user
) -> None:
    ticket = send(branch)
    Notification.objects.all().delete()

    reply_to_ticket(
        ticket=ticket, body="Customer haggled last time.", author=manager_user, internal=True
    )

    assert not Notification.objects.filter(template_key="ticket_reply").exists()

    body = api_client.get(
        reverse("v1:support:ticket-detail", kwargs={"reference": ticket.reference}),
        {"email": "ada@example.com"},
    ).json()
    assert all("haggled" not in reply["body"] for reply in body["replies"])


def test_an_empty_reply_is_refused(branch, site_settings, manager_user) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    with pytest.raises(MessageRejected, match="cannot be empty"):
        reply_to_ticket(ticket=ticket, body="  ", author=manager_user)


def test_resolving_records_who_and_when(branch, site_settings, manager_user) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    resolve_ticket(ticket=ticket, actor=manager_user)

    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.resolved_at is not None
    assert ticket.assigned_to == manager_user
    assert ticket.is_open is False


# ── API ───────────────────────────────────────────────────────────────────────


def test_contact_through_the_api(api_client, branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    response = api_client.post(
        reverse("v1:support:contact"),
        {
            "name": "Ada Obi",
            "email": "ada@example.com",
            "phone": "+2348012345678",
            "reason": "catering",
            "subject": "Big event",
            "message": "Do you cater for 200 people?",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["reference"].startswith("SUP-")
    assert Ticket.objects.count() == 1


def test_a_ticket_needs_the_email_to_view(api_client, branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    url = reverse("v1:support:ticket-detail", kwargs={"reference": ticket.reference})

    assert api_client.get(url).status_code == 404
    assert api_client.get(url, {"email": "ada@example.com"}).status_code == 200
    assert api_client.get(url, {"email": "someone@else.com"}).status_code == 404


def test_a_customer_can_reply_through_the_api(api_client, branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    response = api_client.post(
        f"{reverse('v1:support:ticket-detail', kwargs={'reference': ticket.reference})}"
        f"?email=ada@example.com",
        {"body": "Any update?"},
        format="json",
    )
    assert response.status_code == 201
    assert TicketReply.objects.filter(ticket=ticket).count() == 2


def test_my_tickets_is_scoped(api_client, branch, site_settings, verified_user) -> None:  # type: ignore[no-untyped-def]
    send(branch, user=verified_user)
    send(branch, email="other@example.com")

    api_client.force_authenticate(user=verified_user)
    body = api_client.get(reverse("v1:support:my-tickets")).json()
    assert len(body) == 1
    assert body[0]["requester_email"] == "ada@example.com"


def test_the_open_queue_requires_staff(api_client, branch, site_settings, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    send(branch)
    assert api_client.get(reverse("v1:support:open-tickets")).status_code in (401, 403)

    api_client.force_authenticate(user=kitchen_user)
    body = api_client.get(reverse("v1:support:open-tickets")).json()
    assert body["count"] == 1


# ── FAQ ───────────────────────────────────────────────────────────────────────


def test_the_faq_is_published(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    from apps.support.seed import seed_faq

    seed_faq(branch)
    body = api_client.get(reverse("v1:support:faq")).json()
    assert len(body) == 7
    assert any("deliver" in entry["question"].lower() for entry in body)


def test_the_faq_can_be_filtered_by_category(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    from apps.support.seed import seed_faq

    seed_faq(branch)
    body = api_client.get(reverse("v1:support:faq"), {"category": "Delivery"}).json()
    assert body
    assert all(entry["category"] == "Delivery" for entry in body)


def test_the_tax_answer_follows_the_branch_policy(branch) -> None:  # type: ignore[no-untyped-def]
    """The help page currently claims tax-inclusive pricing while the cart adds
    7.5% on top. The seeded answer follows whatever the branch is actually set to."""
    from apps.support.seed import seed_faq

    branch.prices_include_vat = True
    branch.save()
    seed_faq(branch)
    inclusive = FaqEntry.objects.get(question="Do your prices include tax?").answer
    assert "already included" in inclusive

    FaqEntry.objects.all().delete()
    branch.prices_include_vat = False
    branch.save()
    seed_faq(branch)
    exclusive = FaqEntry.objects.get(question="Do your prices include tax?").answer
    assert "added at checkout" in exclusive


def test_inactive_entries_are_hidden(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    FaqEntry.objects.create(question="Secret", answer="Hidden", is_active=False)
    body = api_client.get(reverse("v1:support:faq")).json()
    assert all(entry["question"] != "Secret" for entry in body)


# ── Remaining branches ────────────────────────────────────────────────────────


def test_no_support_address_configured_skips_the_alert(branch, db) -> None:  # type: ignore[no-untyped-def]
    """Missing configuration must not stop the customer being acknowledged."""
    from apps.core.models import SiteSettings

    row = SiteSettings.load()
    row.support_email = ""
    row.orders_email = ""
    row.save()

    ticket = send(branch)
    assert ticket is not None
    assert Notification.objects.filter(template_key="contact_received").exists()
    assert not Notification.objects.filter(template_key="contact_internal").exists()


def test_the_alert_falls_back_to_the_orders_address(branch, db) -> None:  # type: ignore[no-untyped-def]
    from apps.core.models import SiteSettings

    row = SiteSettings.load()
    row.support_email = ""
    row.orders_email = "orders@kuyashplace.com"
    row.save()

    send(branch)
    assert Notification.objects.get(template_key="contact_internal").recipient == (
        "orders@kuyashplace.com"
    )


def test_staff_can_read_any_ticket(api_client, branch, site_settings, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    api_client.force_authenticate(user=kitchen_user)
    url = reverse("v1:support:ticket-detail", kwargs={"reference": ticket.reference})
    assert api_client.get(url).status_code == 200


def test_a_stranger_cannot_reply(api_client, branch, site_settings) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    response = api_client.post(
        reverse("v1:support:ticket-detail", kwargs={"reference": ticket.reference}),
        {"body": "Let me in"},
        format="json",
    )
    assert response.status_code == 404
    assert TicketReply.objects.filter(ticket=ticket).count() == 1


def test_a_staff_reply_through_the_api_is_attributed(  # type: ignore[no-untyped-def]
    api_client, branch, site_settings, manager_user
) -> None:
    ticket = send(branch)
    api_client.force_authenticate(user=manager_user)
    api_client.post(
        reverse("v1:support:ticket-detail", kwargs={"reference": ticket.reference}),
        {"body": "We can do 200."},
        format="json",
    )
    latest = TicketReply.objects.filter(ticket=ticket).order_by("created_at").last()
    assert latest.author == manager_user


def test_the_admin_resolve_action(branch, site_settings, manager_user) -> None:  # type: ignore[no-untyped-def]
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.support.admin import TicketAdmin

    ticket = send(branch)
    admin = TicketAdmin(Ticket, AdminSite())
    admin.message_user = lambda *args, **kwargs: None  # type: ignore[assignment]

    request = RequestFactory().get("/admin/")
    request.user = manager_user
    admin.mark_resolved(request, Ticket.objects.filter(pk=ticket.pk))

    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.RESOLVED


def test_string_representations(branch, site_settings, manager_user) -> None:  # type: ignore[no-untyped-def]
    ticket = send(branch)
    assert ticket.reference in str(ticket)
    assert "Ada Obi" in str(ContactMessage.objects.get())
    assert "reply" in str(ticket.replies.first())

    note = reply_to_ticket(ticket=ticket, body="note", author=manager_user, internal=True)
    assert "note" in str(note)

    entry = FaqEntry.objects.create(question="Why?", answer="Because")
    assert str(entry) == "Why?"


def test_a_bot_gets_a_quiet_success_when_info_logging_is_on(
    api_client, branch, site_settings, caplog
) -> None:  # type: ignore[no-untyped-def]
    """The quarantine log line passed `extra={"message": ...}` — a name reserved on
    LogRecord. Test settings log above INFO, so the record was never built and this
    passed; in development the same request raised KeyError and returned a 500."""
    import logging

    caplog.set_level(logging.INFO, logger="apps.support.services")

    response = api_client.post(
        reverse("v1:support:contact"),
        {
            "name": "Bot",
            "email": "b@example.com",
            "message": "Hi",
            "website": "http://spam.example",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["reference"] == ""
    assert any(record.getMessage() == "contact_message_quarantined" for record in caplog.records)
