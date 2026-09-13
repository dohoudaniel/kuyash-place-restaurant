"""The chat assistant: stored answers, order lookup, hours and handoff (ADR-012).

Replaces a widget that matched hardcoded words to hardcoded replies — a US phone
number, "dishes start from ₦6.90" — after a fake delay.
"""

from __future__ import annotations

import datetime as dt
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import anonymise_user
from apps.core.models import HolidayOverride, OpeningHours
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.orders.services.placement import place_order
from apps.support import chat
from apps.support.models import ChatSession, FaqEntry, Ticket

pytestmark = pytest.mark.django_db

START = reverse("v1:support:chat-start")


def messages_url(session: ChatSession) -> str:
    return reverse("v1:support:chat-messages", kwargs={"session_id": session.pk})


def detail_url(session: ChatSession) -> str:
    return reverse("v1:support:chat-detail", kwargs={"session_id": session.pk})


def escalate_url(session: ChatSession) -> str:
    return reverse("v1:support:chat-escalate", kwargs={"session_id": session.pk})


@pytest.fixture
def site_settings(db):  # type: ignore[no-untyped-def]
    from apps.core.models import SiteSettings

    row = SiteSettings.load()
    row.support_email = "support@kuyashplace.com"
    row.save()
    return row


@pytest.fixture
def faq(db):  # type: ignore[no-untyped-def]
    delivery = FaqEntry.objects.create(
        question="Where do you deliver?",
        answer="We deliver across Victoria Island, Ikoyi and Lekki Phase 1.",
        category="Delivery",
        keywords=["delivery", "deliver", "area"],
        display_order=1,
    )
    duration = FaqEntry.objects.create(
        question="How long does delivery take?",
        answer="Typically 35–50 minutes.",
        category="Delivery",
        keywords=["how long"],
        display_order=2,
    )
    FaqEntry.objects.create(
        question="Do you have a secret menu?",
        answer="Hidden.",
        keywords=["secret"],
        is_active=False,
    )
    return delivery, duration


@pytest.fixture
def session(branch) -> ChatSession:  # type: ignore[no-untyped-def]
    return chat.start_session(branch=branch)


@pytest.fixture
def order(ready_cart) -> Order:  # type: ignore[no-untyped-def]
    placed = place_order(cart=ready_cart, payment_method="card")
    Order.objects.filter(pk=placed.pk).update(
        status="preparing",
        estimated_delivery_at=dt.datetime(2026, 9, 13, 13, 35, tzinfo=dt.UTC),
    )
    placed.refresh_from_db()
    return placed


def say(session: ChatSession, text: str, user=None) -> chat.BotReply:  # type: ignore[no-untyped-def]
    session.refresh_from_db()
    return chat.respond(session, text, user=user)


# ──────────────────────────────────────────────────────────────────────────────
# FAQ matching
# ──────────────────────────────────────────────────────────────────────────────


def test_a_keyword_returns_the_stored_answer_verbatim(session, faq) -> None:  # type: ignore[no-untyped-def]
    delivery, duration = faq
    reply = say(session, "Do you deliver to Lekki?")
    assert reply.body == delivery.answer
    assert reply.matched_faq == delivery
    assert chat.TALK_TO_HUMAN in reply.suggestions


@pytest.mark.parametrize(
    ("word", "stemmed"),
    [
        ("delivery", "deliver"),
        ("delivering", "deliver"),
        ("deliveries", "deliver"),
        ("weddings", "wedd"),
        ("wedding", "wedd"),
        ("prices", "price"),
        ("hours", "hour"),
        ("glass", "glass"),
        ("bus", "bus"),
    ],
)
def test_the_stemmer_is_crude_but_consistent(word, stemmed) -> None:  # type: ignore[no-untyped-def]
    assert chat.stem(word) == stemmed


def test_the_seeded_faq_answers_everyday_phrasing(session, branch) -> None:  # type: ignore[no-untyped-def]
    """Found in a live run: "Do you deliver to Ikoyi?" missed the keyword "delivery"."""
    from apps.support.seed import seed_faq

    seed_faq(branch)
    cases = {
        "Do you deliver to Ikoyi?": "Where do you deliver?",
        "can i pay with cash": "What payment methods do you accept?",
        "do you do weddings": "Do you cater for events?",
        "is VAT included in your prices": "Do your prices include tax?",
        "I need to cancel": "Can I cancel an order?",
        "book a table for four": "How do I book a table?",
    }
    for text, question in cases.items():
        reply = say(session, text)
        assert reply.matched_faq is not None, text
        assert reply.matched_faq.question == question, text


def test_related_questions_are_suggested(session, faq) -> None:  # type: ignore[no-untyped-def]
    delivery, duration = faq
    reply = say(session, "how long does delivery take")
    assert reply.matched_faq == duration
    assert delivery.question in reply.suggestions


def test_a_suggestion_matches_its_own_answer(session, faq) -> None:  # type: ignore[no-untyped-def]
    _, duration = faq
    assert say(session, duration.question).matched_faq == duration


def test_inactive_answers_are_never_used(session, faq) -> None:  # type: ignore[no-untyped-def]
    reply = say(session, "secret menu secret")
    assert reply.matched_faq is None
    assert "Hidden." not in reply.body


def test_an_unknown_question_is_never_guessed(session, faq) -> None:  # type: ignore[no-untyped-def]
    reply = say(session, "How much is the jollof rice?")
    assert reply.body == chat.FALLBACK
    assert reply.can_escalate
    assert "₦" not in reply.body


def test_weak_overlap_is_not_an_answer(session, faq) -> None:  # type: ignore[no-untyped-def]
    """One shared word is a coincidence, not a match — offer related questions instead."""
    reply = say(session, "take")
    assert reply.matched_faq is None
    assert faq[1].question in reply.suggestions


def test_scoring_ignores_non_string_keywords(faq) -> None:  # type: ignore[no-untyped-def]
    entry = faq[0]
    entry.keywords = ["delivery", 42, None, ""]
    assert chat.score_faq("delivery please", entry) == 3 + 1  # keyword + "deliver" in the question


def test_greetings_and_thanks(session, faq) -> None:  # type: ignore[no-untyped-def]
    assert say(session, "Hello!").body == chat.GREETING
    assert say(session, "good morning").body == chat.GREETING
    assert say(session, "thanks a lot").body == chat.THANKS_REPLY


def test_asking_for_a_person_offers_handoff(session, faq) -> None:  # type: ignore[no-untyped-def]
    for text in ("Can I talk to a human?", "I want to speak to someone", "complaint"):
        reply = say(session, text)
        assert reply.can_escalate, text
        assert reply.body == chat.HANDOFF


# ──────────────────────────────────────────────────────────────────────────────
# Order lookup
# ──────────────────────────────────────────────────────────────────────────────


def test_owners_get_their_order_status_and_a_link(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    reply = say(session, f"where is {order.reference.lower()}", user=verified_user)
    assert reply.body.startswith(f"Order {order.reference} is preparing.")
    assert "Estimated delivery time: 14:35." in reply.body  # Africa/Lagos is UTC+1
    assert reply.action == {
        "type": "order",
        "label": "View order",
        "url": f"/orders/{order.reference}",
    }


def test_a_reference_without_the_dash_is_understood(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    compact = order.reference.replace("-", "")
    assert say(session, compact, user=verified_user).body.startswith(f"Order {order.reference}")


def test_strangers_must_give_the_orders_email(session, order) -> None:  # type: ignore[no-untyped-def]
    ask = say(session, order.reference)
    assert ask.body == chat.ASK_EMAIL
    assert "preparing" not in ask.body

    reply = say(session, "It's ADA@example.com")
    assert reply.body.startswith(f"Order {order.reference} is preparing.")
    assert reply.action is None  # the order page needs the emailed link
    session.refresh_from_db()
    assert session.awaiting == ""


def test_a_wrong_email_and_a_missing_order_look_the_same(session, order) -> None:  # type: ignore[no-untyped-def]
    wrong = say(session, f"{order.reference} mallory@example.com")
    missing = say(session, "KYS-ZZZZZZ ada@example.com")
    assert wrong.body == missing.body == chat.NOT_FOUND
    assert wrong.can_escalate


def test_signed_in_non_owners_are_treated_as_strangers(session, order) -> None:  # type: ignore[no-untyped-def]
    other = User.objects.create_user(email="other@example.com", password="x" * 16)
    assert say(session, order.reference, user=other).body == chat.ASK_EMAIL


def test_track_my_order_finds_the_order_in_progress(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    reply = say(session, chat.TRACK_ORDER, user=verified_user)
    assert reply.body.startswith(f"Order {order.reference}")


def test_track_my_order_with_nothing_in_progress(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(status="delivered", delivered_at=timezone.now())
    reply = say(session, "track my order", user=verified_user)
    assert "don't have an order in progress" in reply.body
    assert reply.action == {"type": "link", "label": "My orders", "url": "/orders"}


def test_track_my_order_asks_guests_for_a_reference_then_reads_it(session, order) -> None:  # type: ignore[no-untyped-def]
    assert say(session, "Where's my order?").body == chat.ASK_REFERENCE
    session.refresh_from_db()
    assert session.awaiting == "order_reference"
    assert say(session, f"{order.reference} ada@example.com").body.startswith("Order")


def test_changing_the_subject_drops_the_pending_question(session, order, faq) -> None:  # type: ignore[no-untyped-def]
    say(session, "track my order")
    reply = say(session, "do you deliver to ikoyi")
    assert reply.matched_faq == faq[0]
    session.refresh_from_db()
    assert session.awaiting == ""


def test_an_empty_answer_to_the_reference_question_repeats_it(session) -> None:  # type: ignore[no-untyped-def]
    say(session, "track my order")
    assert say(session, "?!").body == chat.ASK_REFERENCE


def test_a_delivered_order_says_when(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(
        status="delivered", delivered_at=dt.datetime(2026, 9, 13, 12, 2, tzinfo=dt.UTC)
    )
    assert "delivered at 13:02" in say(session, order.reference, user=verified_user).body


def test_pickup_orders_report_the_ready_time(session, order, verified_user) -> None:  # type: ignore[no-untyped-def]
    Order.objects.filter(pk=order.pk).update(
        fulfilment_type="pickup", estimated_ready_at=dt.datetime(2026, 9, 13, 11, 0, tzinfo=dt.UTC)
    )
    assert "Estimated ready time: 12:00." in say(session, order.reference, user=verified_user).body


# ──────────────────────────────────────────────────────────────────────────────
# Opening hours
# ──────────────────────────────────────────────────────────────────────────────


def lagos(year, month, day, hour, minute=0):  # type: ignore[no-untyped-def]
    from zoneinfo import ZoneInfo

    return dt.datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Africa/Lagos"))


@pytest.fixture
def lunch_and_dinner(branch):  # type: ignore[no-untyped-def]
    """11:00–15:00 and 18:00–22:00 every day."""
    OpeningHours.objects.filter(branch=branch).delete()
    for weekday in range(7):
        OpeningHours.objects.create(
            branch=branch,
            weekday=weekday,
            service="lunch",
            opens_at=dt.time(11),
            closes_at=dt.time(15),
        )
        OpeningHours.objects.create(
            branch=branch,
            weekday=weekday,
            service="dinner",
            opens_at=dt.time(18),
            closes_at=dt.time(22),
        )
    return branch


def at(moment):  # type: ignore[no-untyped-def]
    return mock.patch("apps.core.models.Branch.local_now", return_value=moment)


def test_open_now_says_until_when(session, lunch_and_dinner) -> None:  # type: ignore[no-untyped-def]
    with at(lagos(2026, 9, 14, 12)):
        reply = say(session, "are you open?")
    assert reply.body == "We're open now until 15:00."
    assert reply.action == {"type": "link", "label": "Opening hours", "url": "/contact"}


def test_closed_between_services_says_when_it_opens(session, lunch_and_dinner) -> None:  # type: ignore[no-untyped-def]
    with at(lagos(2026, 9, 14, 16)):
        assert (
            say(session, "opening hours").body
            == "We're closed right now. We open again today at 18:00."
        )
    with at(lagos(2026, 9, 14, 23)):
        assert (
            say(session, "what time do you open").body
            == "We're closed right now. We open again tomorrow at 11:00."
        )


def test_closed_for_days_names_the_day(session, lunch_and_dinner) -> None:  # type: ignore[no-untyped-def]
    for offset in (1, 2):
        HolidayOverride.objects.create(
            branch=lunch_and_dinner,
            date=dt.date(2026, 9, 14) + dt.timedelta(days=offset),
            is_closed=True,
        )
    with at(lagos(2026, 9, 14, 23)):
        assert (
            say(session, "hours").body
            == "We're closed right now. We open again on Thursday at 11:00."
        )


def test_closed_indefinitely(session, branch) -> None:  # type: ignore[no-untyped-def]
    OpeningHours.objects.filter(branch=branch).update(is_closed=True)
    reply = say(session, "are you open")
    assert reply.body.startswith("We're closed at the moment.")
    assert reply.can_escalate


def test_a_holiday_with_short_hours(session, lunch_and_dinner) -> None:  # type: ignore[no-untyped-def]
    HolidayOverride.objects.create(
        branch=lunch_and_dinner,
        date=dt.date(2026, 9, 14),
        is_closed=False,
        opens_at=dt.time(10),
        closes_at=dt.time(13),
    )
    with at(lagos(2026, 9, 14, 12)):
        assert say(session, "open?").body == "We're open now until 13:00."


def test_open_without_a_listed_window(session, lunch_and_dinner) -> None:  # type: ignore[no-untyped-def]
    HolidayOverride.objects.create(
        branch=lunch_and_dinner, date=dt.date(2026, 9, 14), is_closed=False
    )
    with at(lagos(2026, 9, 14, 23)):
        assert say(session, "open?").body == "We're open now."


# ──────────────────────────────────────────────────────────────────────────────
# Sessions, limits and handoff (services)
# ──────────────────────────────────────────────────────────────────────────────


def test_a_session_starts_with_a_greeting(session) -> None:  # type: ignore[no-untyped-def]
    greeting = session.messages.get()
    assert greeting.sender == "bot"
    assert greeting.body == chat.GREETING
    assert greeting.extra["suggestions"] == chat.DEFAULT_SUGGESTIONS
    assert len(session.session_token) >= 40


def test_post_message_records_both_sides(session, faq) -> None:  # type: ignore[no-untyped-def]
    customer, bot = chat.post_message(session, "delivery areas?")
    assert customer.sender == "user"
    assert bot.matched_faq == faq[0]
    assert session.messages.count() == 3


def test_long_conversations_are_capped(session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(chat, "MAX_MESSAGES", 2)
    with pytest.raises(chat.ChatLimitReached):
        chat.post_message(session, "hello")  # greeting + 2 > 2


def test_idle_sessions_expire(session) -> None:  # type: ignore[no-untyped-def]
    ChatSession.objects.filter(pk=session.pk).update(
        updated_at=timezone.now() - dt.timedelta(hours=13)
    )
    session.refresh_from_db()
    with pytest.raises(chat.ChatExpired):
        chat.post_message(session, "hello")


def test_escalation_opens_a_ticket_with_the_transcript(session, faq, site_settings) -> None:  # type: ignore[no-untyped-def]
    chat.post_message(session, "My jollof was cold")
    ticket, reply = chat.escalate(
        session, name="Ada Obi", email="ADA@example.com", note="Please call back"
    )

    assert ticket is not None and reply is not None
    assert ticket.subject == "Chat: Please call back"
    assert ticket.requester_email == "ada@example.com"
    body = ticket.replies.get().body
    assert body.startswith("Please call back")
    assert "Customer: My jollof was cold" in body
    assert "Assistant: " in body
    assert ticket.reference in reply.body
    assert set(Notification.objects.values_list("template_key", flat=True)) >= {
        "contact_received",
        "contact_internal",
    }

    session.refresh_from_db()
    assert session.escalated_to_ticket == ticket
    assert session.ended_at is not None
    with pytest.raises(chat.ChatEnded):
        chat.post_message(session, "hello?")

    again, no_reply = chat.escalate(session, name="Ada", email="ada@example.com")
    assert again == ticket and no_reply is None
    assert Ticket.objects.count() == 1


def test_escalation_subject_falls_back_to_the_first_question(session) -> None:  # type: ignore[no-untyped-def]
    chat.post_message(session, "Can I bring my own cake?\nIt's a birthday")
    ticket, _ = chat.escalate(session, name="Ada", email="ada@example.com")
    assert ticket is not None
    assert ticket.subject == "Chat: Can I bring my own cake?"


def test_escalating_nothing_is_refused(session) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(chat.EscalationEmpty):
        chat.escalate(session, name="Ada", email="ada@example.com")


def test_spam_escalations_are_quarantined_quietly(session) -> None:  # type: ignore[no-untyped-def]
    chat.post_message(session, "cheap casino bonus")
    ticket, reply = chat.escalate(session, name="Bot", email="bot@example.com")
    assert ticket is None and reply is None
    assert not Ticket.objects.exists()
    session.refresh_from_db()
    assert session.ended_at is not None
    with pytest.raises(chat.ChatEnded):
        chat.escalate(session, name="Bot", email="bot@example.com", note="again")


def test_erasure_deletes_a_customers_chats(branch, verified_user) -> None:  # type: ignore[no-untyped-def]
    chat.start_session(branch=branch, user=verified_user)
    chat.start_session(branch=branch)
    anonymise_user(verified_user)
    assert ChatSession.objects.count() == 1


def test_labels(session) -> None:  # type: ignore[no-untyped-def]
    assert str(session).startswith("Chat ")
    assert str(session.messages.get()).startswith("Assistant: Hi!")


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def started(api_client, branch):  # type: ignore[no-untyped-def]
    body = api_client.post(START).json()
    return ChatSession.objects.get(pk=body["id"]), body["token"], body


def test_starting_returns_a_token_and_the_greeting(started) -> None:  # type: ignore[no-untyped-def]
    session, token, body = started
    assert token == session.session_token
    assert body["messages"] == [
        {
            "sender": "bot",
            "body": chat.GREETING,
            "created_at": body["messages"][0]["created_at"],
            "suggestions": chat.DEFAULT_SUGGESTIONS,
            "can_escalate": False,
            "action": None,
        }
    ]
    assert body["is_ended"] is False
    assert body["escalated_reference"] is None


def test_the_token_is_required(api_client, started) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    assert api_client.get(detail_url(session)).status_code == 404
    assert api_client.get(detail_url(session), HTTP_X_CHAT_TOKEN="wrong").status_code == 404
    assert api_client.post(messages_url(session), {"body": "hi"}, format="json").status_code == 404
    assert api_client.get(detail_url(session), HTTP_X_CHAT_TOKEN=token).status_code == 200


def test_unknown_sessions_are_not_found(api_client, branch) -> None:  # type: ignore[no-untyped-def]
    import uuid

    url = reverse("v1:support:chat-detail", kwargs={"session_id": uuid.uuid4()})
    assert api_client.get(url).status_code == 404


def test_sending_returns_both_messages(api_client, started, faq) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    response = api_client.post(
        messages_url(session),
        {"body": "  where do you deliver  "},
        format="json",
        HTTP_X_CHAT_TOKEN=token,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["message"]["sender"] == "user"
    assert body["message"]["body"] == "where do you deliver"
    assert body["reply"]["body"] == faq[0].answer

    history = api_client.get(detail_url(session), HTTP_X_CHAT_TOKEN=token).json()
    assert [m["sender"] for m in history["messages"]] == ["bot", "user", "bot"]


def test_messages_are_length_limited(api_client, started) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    response = api_client.post(
        messages_url(session), {"body": "x" * 501}, format="json", HTTP_X_CHAT_TOKEN=token
    )
    assert response.status_code == 400


def test_signed_in_owners_need_no_token(api_client, branch, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    session = ChatSession.objects.get(pk=api_client.post(START).json()["id"])
    assert session.user == verified_user
    assert api_client.get(detail_url(session)).status_code == 200

    other = User.objects.create_user(email="other@example.com", password="x" * 16)
    api_client.force_authenticate(other)
    assert api_client.get(detail_url(session)).status_code == 404


def test_guest_escalation_needs_name_and_email(api_client, started) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    api_client.post(
        messages_url(session), {"body": "cold food"}, format="json", HTTP_X_CHAT_TOKEN=token
    )
    response = api_client.post(escalate_url(session), {}, format="json", HTTP_X_CHAT_TOKEN=token)
    assert response.status_code == 400
    assert set(response.json()["errors"]) == {"name", "email"}


def test_guest_escalation(api_client, started) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    api_client.post(
        messages_url(session), {"body": "cold food"}, format="json", HTTP_X_CHAT_TOKEN=token
    )
    response = api_client.post(
        escalate_url(session),
        {"name": "Ada", "email": "ada@example.com"},
        format="json",
        HTTP_X_CHAT_TOKEN=token,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("SUP-")
    assert body["reply"]["sender"] == "bot"

    history = api_client.get(detail_url(session), HTTP_X_CHAT_TOKEN=token).json()
    assert history["is_ended"] is True
    assert history["escalated_reference"] == body["reference"]

    ended = api_client.post(
        messages_url(session), {"body": "hello?"}, format="json", HTTP_X_CHAT_TOKEN=token
    )
    assert ended.status_code == 409
    assert ended.json()["code"] == "chat_ended"

    again = api_client.post(escalate_url(session), {}, format="json", HTTP_X_CHAT_TOKEN=token)
    assert again.status_code == 201
    assert again.json() == {"reference": body["reference"], "reply": None}


def test_signed_in_escalation_uses_the_account(api_client, branch, verified_user) -> None:  # type: ignore[no-untyped-def]
    api_client.force_authenticate(verified_user)
    session = ChatSession.objects.get(pk=api_client.post(START).json()["id"])
    response = api_client.post(
        escalate_url(session), {"message": "Allergy question"}, format="json"
    )
    assert response.status_code == 201
    ticket = Ticket.objects.get()
    assert ticket.user == verified_user
    assert ticket.requester_email == "ada@example.com"
    assert ticket.requester_name == "Ada Obi"


def test_quarantined_escalation_looks_normal(api_client, started) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    response = api_client.post(
        escalate_url(session),
        {"name": "Bot", "email": "bot@example.com", "message": "seo services backlinks"},
        format="json",
        HTTP_X_CHAT_TOKEN=token,
    )
    assert response.status_code == 201
    assert response.json() == {"reference": "", "reply": None}


def test_admin_shows_transcripts(client, started) -> None:  # type: ignore[no-untyped-def]
    session, _, _ = started
    admin = User.objects.create_superuser(email="root@example.com", password="x" * 16)
    client.force_login(admin)
    assert client.get(reverse("admin:support_chatsession_changelist")).status_code == 200
    page = client.get(reverse("admin:support_chatsession_change", args=[session.pk]))
    assert page.status_code == 200
    assert "Kuyash Place assistant" in page.content.decode()
    assert client.get(reverse("admin:support_chatsession_add")).status_code == 403


def test_chat_messages_are_rate_limited(api_client, started, throttle_rates) -> None:  # type: ignore[no-untyped-def]
    session, token, _ = started
    with throttle_rates(chat_message="2/min"):
        codes = [
            api_client.post(
                messages_url(session), {"body": "hi"}, format="json", HTTP_X_CHAT_TOKEN=token
            ).status_code
            for _ in range(3)
        ]
    assert codes == [201, 201, 429]
