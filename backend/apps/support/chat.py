"""The chat assistant (ADR-012, SUP-5).

It can do exactly four things, all from stored data:

1. repeat an admin-written FAQ answer matched by keywords,
2. report the status of an order the visitor can show is theirs,
3. read the branch's opening hours,
4. hand the conversation to a person as a support ticket.

It never composes an answer of its own, so it cannot promise a price, a fee or
a delivery time that nobody wrote down.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework import status

from apps.common.exceptions import DomainError
from apps.core.selectors import next_opening
from apps.orders.models import Order, OrderStatus
from apps.support.models import (
    ChatMessage,
    ChatSender,
    ChatSession,
    ContactReason,
    FaqEntry,
    Ticket,
    TicketReply,
)

MAX_MESSAGE_LENGTH = 500
#: Both sides counted. A conversation this long needs a person, not more bot.
MAX_MESSAGES = 60
IDLE_LIMIT = dt.timedelta(hours=12)
FAQ_THRESHOLD = 3
RELATED_LIMIT = 2

GREETING = (
    "Hi! I'm the Kuyash Place assistant. I can answer common questions, check on "
    "an order, or put you in touch with our team."
)
FALLBACK = (
    "I'm not sure about that one, and I'd rather not guess. I can pass your "
    "question to our team — they'll reply by email."
)
ASK_REFERENCE = (
    "Sure — what's your order reference? It starts with KYS- and is in your confirmation email."
)
ASK_EMAIL = "For your security, what email address did you use for that order?"
NOT_FOUND = (
    "I couldn't find an order matching those details. Check the reference in your "
    "confirmation email, or I can pass this to our team."
)
HANDOFF = "Of course. Leave your details and our team will pick this up and reply by email."
THANKS_REPLY = "You're welcome! Is there anything else I can help with?"

TRACK_ORDER = "Track my order"
OPENING_HOURS = "Opening hours"
TALK_TO_HUMAN = "Talk to a human"
DEFAULT_SUGGESTIONS = [TRACK_ORDER, OPENING_HOURS, TALK_TO_HUMAN]

REFERENCE_RE = re.compile(r"\bKYS-?([23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6})\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
WORD_RE = re.compile(r"[a-z0-9']+")

STOPWORDS = frozenset(
    "a an and are at be can could do does for from have how i if in is it me my of on or "
    "our please the to we what when where which who why will with you your".split()
)
HUMAN_WORDS = frozenset(
    {"human", "agent", "person", "someone", "staff", "representative", "manager"}
)
HUMAN_PHRASES = ("talk to", "speak to", "speak with", "call me", "complaint", "complain")
ORDER_PHRASES = ("track", "my order", "order status", "where is my", "where's my", "wheres my")
HOURS_WORDS = frozenset({"hours", "open", "opening", "close", "closing", "closed"})
GREETING_WORDS = frozenset(
    {"hi", "hello", "hey", "hiya", "good", "morning", "afternoon", "evening"}
)
THANKS_WORDS = frozenset({"thanks", "thank", "cheers"})

ACTIVE_STATUSES = frozenset(
    {
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.FAILED_DELIVERY,
    }
)


class ChatUnavailable(DomainError):
    status_code = status.HTTP_409_CONFLICT


class ChatEnded(ChatUnavailable):
    code = "chat_ended"
    title = "This conversation has ended"


class ChatExpired(ChatUnavailable):
    code = "chat_expired"
    title = "This conversation has timed out"


class ChatLimitReached(ChatUnavailable):
    code = "chat_limit"
    title = "This conversation is too long to continue"


class EscalationEmpty(DomainError):
    code = "message_rejected"
    status_code = 422
    title = "Tell us what you need help with"


@dataclass
class BotReply:
    body: str
    matched_faq: FaqEntry | None = None
    suggestions: list[str] = field(default_factory=lambda: list(DEFAULT_SUGGESTIONS))
    can_escalate: bool = False
    action: dict[str, str] | None = None

    def extra(self) -> dict[str, Any]:
        return {
            "suggestions": self.suggestions,
            "can_escalate": self.can_escalate,
            "action": self.action,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Matching
# ──────────────────────────────────────────────────────────────────────────────


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


#: Longest first. Just enough that "deliver", "delivery" and "delivering" meet.
SUFFIXES = (("ies", "y"), ("ery", "er"), ("ing", ""), ("ed", ""), ("s", ""))


def stem(word: str) -> str:
    """A deliberately crude stemmer — matching, not linguistics.

    Applied until nothing changes, so "weddings" and "wedding" end up equal
    however many suffixes they carry.
    """
    while True:
        for suffix, replacement in SUFFIXES:
            if (
                len(word) > len(suffix) + 3
                and word.endswith(suffix)
                and not (suffix == "s" and word.endswith("ss"))
            ):
                word = word[: -len(suffix)] + replacement
                break
        else:
            return word


def stems(text: str) -> list[str]:
    return [stem(word) for word in words(text)]


def _padded(text: str) -> str:
    return f" {' '.join(words(text))} "


def _padded_stems(text: str) -> str:
    return f" {' '.join(stems(text))} "


def score_faq(text: str, entry: FaqEntry) -> int:
    """Three points per keyword phrase present, one per shared question word.

    Both sides are stemmed, so the keyword "delivery" matches "do you deliver".
    """
    padded = _padded_stems(text)
    # A set: "delivery" and "deliver" stem alike and must not count twice.
    phrases = {
        _padded_stems(keyword)
        for keyword in entry.keywords or []
        if isinstance(keyword, str) and words(keyword)
    }
    score = sum(3 for phrase in phrases if phrase in padded)
    meaningful = {stem(word) for word in words(text) if word not in STOPWORDS}
    question = {stem(word) for word in words(entry.question) if word not in STOPWORDS}
    return score + len(meaningful & question)


def match_faq(text: str) -> tuple[FaqEntry | None, list[FaqEntry]]:
    """The best answer above the threshold, and a couple of related questions."""
    scored = [
        (score, entry)
        for entry in FaqEntry.objects.filter(is_active=True)
        if (score := score_faq(text, entry)) > 0
    ]
    # Stable: equal scores keep the admin's ordering.
    scored.sort(key=lambda pair: -pair[0])
    if not scored or scored[0][0] < FAQ_THRESHOLD:
        return None, [entry for _, entry in scored[:RELATED_LIMIT]]
    return scored[0][1], [entry for _, entry in scored[1 : 1 + RELATED_LIMIT]]


def _normalise_reference(raw: str) -> str:
    return f"KYS-{raw.upper()}"


# ──────────────────────────────────────────────────────────────────────────────
# Answers from stored data
# ──────────────────────────────────────────────────────────────────────────────


def _clock(moment: dt.datetime, tz: dt.tzinfo) -> str:
    return timezone.localtime(moment, timezone=tz).strftime("%H:%M")


def order_status_reply(order: Order, *, owner: bool) -> BotReply:
    tz = order.branch.tzinfo()
    lines = [f"Order {order.reference} is {order.get_status_display().lower()}."]
    if order.status in ACTIVE_STATUSES:
        estimate = (
            order.estimated_delivery_at
            if order.fulfilment_type == "delivery"
            else order.estimated_ready_at
        )
        if estimate:
            label = "delivery" if order.fulfilment_type == "delivery" else "ready"
            lines.append(f"Estimated {label} time: {_clock(estimate, tz)}.")
    elif order.status == OrderStatus.DELIVERED and order.delivered_at:
        lines.append(f"It was delivered at {_clock(order.delivered_at, tz)}.")
    if not owner:
        lines.append("The link in your confirmation email shows live updates.")
    return BotReply(
        body=" ".join(lines),
        action=(
            {"type": "order", "label": "View order", "url": f"/orders/{order.reference}"}
            if owner
            else None
        ),
        suggestions=[OPENING_HOURS, TALK_TO_HUMAN],
    )


def lookup_order(session: ChatSession, *, reference: str, email: str, user: Any) -> BotReply:
    """Status for an order the visitor owns, or whose email they can give.

    A missing order and a wrong email get the same reply, so the assistant cannot
    be used to test which references exist.
    """
    order = Order.objects.select_related("branch").filter(reference=reference).first()
    if order and user is not None and order.user_id and order.user_id == user.pk:
        _clear_awaiting(session)
        return order_status_reply(order, owner=True)

    if not email:
        session.awaiting = "order_email"
        session.context = {"reference": reference}
        session.save(update_fields=["awaiting", "context", "updated_at"])
        return BotReply(body=ASK_EMAIL, suggestions=[TALK_TO_HUMAN])

    _clear_awaiting(session)
    if (
        order
        and order.contact_email
        and constant_time_compare(order.contact_email.lower(), email.lower())
    ):
        return order_status_reply(order, owner=False)
    return BotReply(body=NOT_FOUND, can_escalate=True, suggestions=[TRACK_ORDER, TALK_TO_HUMAN])


def track_for_user(session: ChatSession, user: Any) -> BotReply:
    """ "Track my order": a signed-in customer's order in progress, else ask."""
    if user is not None:
        order = (
            Order.objects.select_related("branch")
            .filter(user=user, status__in=ACTIVE_STATUSES)
            .order_by("-created_at")
            .first()
        )
        if order:
            return order_status_reply(order, owner=True)
        if Order.objects.filter(user=user).exists():
            return BotReply(
                body=(
                    "You don't have an order in progress. Your past orders are on your orders page."
                ),
                action={"type": "link", "label": "My orders", "url": "/orders"},
            )
    session.awaiting = "order_reference"
    session.context = {}
    session.save(update_fields=["awaiting", "context", "updated_at"])
    return BotReply(body=ASK_REFERENCE, suggestions=[TALK_TO_HUMAN])


def hours_reply(branch: Any) -> BotReply:
    tz = branch.tzinfo()
    now = branch.local_now()
    action = {"type": "link", "label": "Opening hours", "url": "/contact"}
    if branch.is_open_now:
        override = branch.holiday_overrides.filter(date=now.date()).first()
        if override is not None and override.closes_at:
            closes: dt.time | None = override.closes_at
        else:
            windows = branch.opening_hours.filter(weekday=now.weekday(), is_closed=False)
            closes = next(
                (w.closes_at for w in windows if w.opens_at <= now.time() <= w.closes_at), None
            )
        body = f"We're open now until {closes.strftime('%H:%M')}." if closes else "We're open now."
        return BotReply(body=body, action=action)

    opening = next_opening(branch)
    if opening is None:
        return BotReply(
            body="We're closed at the moment. Please check our contact page for updates.",
            action=action,
            can_escalate=True,
        )
    opening = timezone.localtime(opening, timezone=tz)
    days = (opening.date() - now.date()).days
    day = "today" if days == 0 else "tomorrow" if days == 1 else f"on {opening.strftime('%A')}"
    return BotReply(
        body=f"We're closed right now. We open again {day} at {opening.strftime('%H:%M')}.",
        action=action,
    )


# ──────────────────────────────────────────────────────────────────────────────
# The conversation
# ──────────────────────────────────────────────────────────────────────────────


def _clear_awaiting(session: ChatSession) -> None:
    if session.awaiting or session.context:
        session.awaiting = ""
        session.context = {}
        session.save(update_fields=["awaiting", "context", "updated_at"])


def respond(session: ChatSession, text: str, *, user: Any = None) -> BotReply:
    """Decide the assistant's reply. Order matters: specific intents first."""
    tokens = words(text)
    token_set = set(tokens)
    padded = _padded(text)
    reference_match = REFERENCE_RE.search(text)
    email_match = EMAIL_RE.search(text)
    email = email_match.group(0) if email_match else ""

    if session.awaiting == "order_email" and email:
        reference = str(session.context.get("reference", ""))
        return lookup_order(session, reference=reference, email=email, user=user)

    if reference_match:
        return lookup_order(
            session,
            reference=_normalise_reference(reference_match.group(1)),
            email=email,
            user=user,
        )

    wants_human = bool(token_set & HUMAN_WORDS) or any(f" {p} " in padded for p in HUMAN_PHRASES)
    if wants_human:
        _clear_awaiting(session)
        return BotReply(body=HANDOFF, can_escalate=True, suggestions=[])

    if session.awaiting == "order_reference" and not tokens:
        return BotReply(body=ASK_REFERENCE, suggestions=[TALK_TO_HUMAN])
    _clear_awaiting(session)

    if any(f" {p} " in padded or padded.strip().startswith(p) for p in ORDER_PHRASES):
        return track_for_user(session, user)

    if token_set & HOURS_WORDS:
        return hours_reply(session.branch)

    if tokens and len(tokens) <= 3 and token_set <= GREETING_WORDS:
        return BotReply(body=GREETING)
    if token_set & THANKS_WORDS and len(tokens) <= 4:
        return BotReply(body=THANKS_REPLY)

    entry, related = match_faq(text)
    if entry is not None:
        return BotReply(
            body=entry.answer,
            matched_faq=entry,
            suggestions=[item.question for item in related] + [TALK_TO_HUMAN],
        )
    return BotReply(
        body=FALLBACK,
        can_escalate=True,
        suggestions=[item.question for item in related] or [TRACK_ORDER, OPENING_HOURS],
    )


def _bot_message(session: ChatSession, reply: BotReply) -> ChatMessage:
    return ChatMessage.objects.create(
        session=session,
        sender=ChatSender.BOT,
        body=reply.body,
        matched_faq=reply.matched_faq,
        extra=reply.extra(),
    )


@transaction.atomic
def start_session(*, branch: Any, user: Any = None) -> ChatSession:
    session = ChatSession.objects.create(branch=branch, user=user)
    _bot_message(session, BotReply(body=GREETING))
    return session


def ensure_open(session: ChatSession, *, now: dt.datetime | None = None) -> None:
    if session.ended_at is not None:
        raise ChatEnded("Start a new conversation if you need anything else.")
    if (now or timezone.now()) - session.updated_at > IDLE_LIMIT:
        raise ChatExpired("Start a new conversation to carry on.")


@transaction.atomic
def post_message(
    session: ChatSession, text: str, *, user: Any = None
) -> tuple[ChatMessage, ChatMessage]:
    session = ChatSession.objects.select_for_update().select_related("branch").get(pk=session.pk)
    ensure_open(session)
    if session.messages.count() + 2 > MAX_MESSAGES:
        raise ChatLimitReached("Our team can take it from here — ask to talk to a human.")

    customer = ChatMessage.objects.create(session=session, sender=ChatSender.USER, body=text)
    reply = respond(session, text, user=user)
    bot = _bot_message(session, reply)
    session.save(update_fields=["updated_at"])
    return customer, bot


def transcript(session: ChatSession) -> str:
    return "\n".join(
        f"{message.get_sender_display()}: {message.body}" for message in session.messages.all()
    )


@transaction.atomic
def escalate(
    session: ChatSession, *, name: str, email: str, note: str = "", user: Any = None
) -> tuple[Ticket | None, ChatMessage | None]:
    """Turn the conversation into a ticket. Safe to call twice."""
    from apps.support.services import _acknowledge, _alert_team, looks_like_spam

    session = ChatSession.objects.select_for_update().get(pk=session.pk)
    if session.escalated_to_ticket_id:
        return session.escalated_to_ticket, None
    if session.ended_at is not None:
        raise ChatEnded("Start a new conversation if you need anything else.")

    first_question = (
        session.messages.filter(sender=ChatSender.USER).values_list("body", flat=True).first()
    )
    if not (note.strip() or first_question):
        raise EscalationEmpty("Tell us what you need help with.")

    history = transcript(session)
    now = timezone.now()
    if looks_like_spam(message=f"{note}\n{history}"):
        session.ended_at = now
        session.save(update_fields=["ended_at", "updated_at"])
        return None, None

    summary = (note.strip() or first_question or "").splitlines()[0][:80]
    ticket = Ticket.objects.create(
        branch=session.branch,
        user=user,
        requester_name=name.strip(),
        requester_email=email.strip().lower(),
        subject=f"Chat: {summary}",
        reason=ContactReason.GENERAL,
    )
    body = note.strip()
    TicketReply.objects.create(
        ticket=ticket,
        body=(f"{body}\n\n" if body else "") + f"— Chat transcript —\n{history}",
    )
    _acknowledge(ticket)
    _alert_team(ticket)

    session.escalated_to_ticket = ticket
    session.ended_at = now
    session.save(update_fields=["escalated_to_ticket", "ended_at", "updated_at"])
    first_name = ticket.requester_name.split(" ")[0] or "there"
    message = _bot_message(
        session,
        BotReply(
            body=(
                f"Thanks, {first_name}. I've passed this to our team — your reference is "
                f"{ticket.reference}, and we'll reply to {ticket.requester_email}."
            ),
            suggestions=[],
        ),
    )
    return ticket, message
