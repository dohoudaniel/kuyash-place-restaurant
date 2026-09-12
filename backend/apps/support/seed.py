"""FAQ seed data.

Carried over from ``app/help/page.tsx``. One answer is corrected: the page
currently claims prices include tax while the cart adds 7.5% on top. The
wording here follows the branch's actual VAT policy instead.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.support.models import FaqEntry


def _vat_answer(branch: Any) -> str:
    if branch.prices_include_vat:
        return (
            "Yes. The price shown is the price you pay — VAT is already included. "
            "Delivery is charged separately and shown before you confirm."
        )
    return (
        "Menu prices are shown before VAT. VAT is added at checkout and itemised "
        "in your order summary, along with any delivery fee."
    )


def faq_entries(branch: Any) -> list[dict[str, Any]]:
    return [
        {
            "question": "Do your prices include tax?",
            "answer": _vat_answer(branch),
            "category": "Ordering",
            "display_order": 1,
            "keywords": ["vat", "tax", "price"],
        },
        {
            "question": "Where do you deliver?",
            "answer": (
                "We deliver across Victoria Island, Ikoyi and Lekki Phase 1. "
                "Enter your address at checkout and we will show the fee and the "
                "estimated time, or offer collection if you are outside those areas."
            ),
            "category": "Delivery",
            "display_order": 1,
            "keywords": ["delivery", "area", "zone", "where"],
        },
        {
            "question": "How long does delivery take?",
            "answer": (
                "Typically 35–50 minutes depending on your area and how busy the "
                "kitchen is. Your order page shows a live estimate and updates as "
                "the kitchen works."
            ),
            "category": "Delivery",
            "display_order": 2,
            "keywords": ["how long", "time", "eta"],
        },
        {
            "question": "Can I cancel an order?",
            "answer": (
                "Yes, until the kitchen starts preparing it. After that please call "
                "us and we will do what we can."
            ),
            "category": "Ordering",
            "display_order": 2,
            "keywords": ["cancel", "refund", "change"],
        },
        {
            "question": "How do I book a table?",
            "answer": (
                "Use the reservations page. Pick a date, party size and area, and we "
                "will show you the times that are genuinely free. You will get a "
                "confirmation email with a link to change or cancel the booking."
            ),
            "category": "Reservations",
            "display_order": 1,
            "keywords": ["book", "table", "reservation"],
        },
        {
            "question": "Do you cater for events?",
            "answer": (
                "We do, from 10 to 500 guests. Send an enquiry through the catering "
                "page and a member of our team will come back to you within 24 hours "
                "with a quote."
            ),
            "category": "Catering",
            "display_order": 1,
            "keywords": ["catering", "event", "wedding", "party"],
        },
        {
            "question": "What payment methods do you accept?",
            "answer": (
                "Card and bank transfer online, or cash on delivery. Card payments "
                "are handled by our payment provider — we never see or store your "
                "card details."
            ),
            "category": "Payment",
            "display_order": 1,
            "keywords": ["payment", "card", "cash", "transfer"],
        },
    ]


@transaction.atomic
def seed_faq(branch: Any, *, stdout: Any = None) -> int:
    created = 0
    for payload in faq_entries(branch):
        _, made = FaqEntry.objects.get_or_create(
            question=payload["question"],
            defaults={k: v for k, v in payload.items() if k != "question"},
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} FAQ entries")
    return created
