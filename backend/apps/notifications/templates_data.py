"""Built-in email wording.

These are the fallbacks. Staff override them in the admin; if a row is missing,
inactive or malformed, the system falls back here rather than failing to send.
An order confirmation that is slightly off-brand beats one that never arrives.
"""

from __future__ import annotations

from typing import Any

SIGN_OFF = "\n\n— Kuyash Place\n"

DEFAULT_TEMPLATES: dict[str, dict[str, Any]] = {
    "verify_email": {
        "description": "Sent on registration to confirm the address.",
        "subject": "Confirm your email — Kuyash Place",
        "text_body": (
            "Hello {name},\n\n"
            "Confirm your email address to finish setting up your Kuyash Place account:\n\n"
            "{link}\n\n"
            "If you did not create an account, you can ignore this message." + SIGN_OFF
        ),
        "available_context": ["name", "link"],
    },
    "password_reset": {
        "description": "Sent when a password reset is requested.",
        "subject": "Reset your password — Kuyash Place",
        "text_body": (
            "Hello {name},\n\n"
            "Use the link below to choose a new password. It expires in one hour.\n\n"
            "{link}\n\n"
            "If you did not request this, you can ignore this message and your password "
            "will stay unchanged." + SIGN_OFF
        ),
        "available_context": ["name", "link"],
    },
    "order_confirmation": {
        "description": "Sent when payment is confirmed.",
        "subject": "Order {reference} confirmed",
        "text_body": (
            "Hello {name},\n\n"
            "Thank you — we have your payment and the kitchen has your order.\n\n"
            "Order:  {reference}\n"
            "Total:  {total}\n"
            "{fulfilment_line}\n"
            "Track it here: {tracking_url}" + SIGN_OFF
        ),
        "available_context": [
            "name",
            "reference",
            "total",
            "fulfilment_line",
            "tracking_url",
        ],
    },
    "order_accepted": {
        "description": "Sent when the kitchen accepts an order.",
        "subject": "Order {reference} is being prepared",
        "text_body": (
            "Hello {name},\n\n"
            "The kitchen has started on your order.\n\n"
            "Order: {reference}\n"
            "{eta_line}\n"
            "Track it here: {tracking_url}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "eta_line", "tracking_url"],
    },
    "order_ready": {
        "description": "Sent when a pickup order is ready for collection.",
        "subject": "Order {reference} is ready for collection",
        "text_body": (
            "Hello {name},\n\n"
            "Your order is ready. Come and collect it whenever suits you.\n\n"
            "Order: {reference}" + SIGN_OFF
        ),
        "available_context": ["name", "reference"],
    },
    "order_out_for_delivery": {
        "description": "Sent when a rider collects the order.",
        "subject": "Order {reference} is on the way",
        "text_body": (
            "Hello {name},\n\n"
            "Your order has left the restaurant.\n\n"
            "Order: {reference}\n"
            "{rider_line}\n"
            "Track it here: {tracking_url}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "rider_line", "tracking_url"],
    },
    "order_delivered": {
        "description": "Sent on delivery.",
        "subject": "Order {reference} delivered",
        "text_body": (
            "Hello {name},\n\n"
            "Enjoy your meal. We would love to hear how it was.\n\n"
            "Order: {reference}" + SIGN_OFF
        ),
        "available_context": ["name", "reference"],
    },
    "order_rejected": {
        "description": "Sent when the kitchen cannot fulfil an order.",
        "subject": "Order {reference} could not be fulfilled",
        "text_body": (
            "Hello {name},\n\n"
            "We are sorry — the kitchen could not take this order.\n"
            "{refund_line}\n\n"
            "Order: {reference}\n"
            "{reason_line}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "refund_line", "reason_line"],
    },
    "order_cancelled": {
        "description": "Sent when an order is cancelled.",
        "subject": "Order {reference} cancelled",
        "text_body": (
            "Hello {name},\n\n"
            "Your order has been cancelled.\n"
            "{refund_line}\n\n"
            "Order: {reference}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "refund_line"],
    },
    "refund_issued": {
        "description": "Sent when a refund is processed.",
        "subject": "Refund for order {reference}",
        "text_body": (
            "Hello {name},\n\n"
            "We have refunded {amount} for order {reference}.\n"
            "It can take a few working days to appear on your statement.\n"
            "{reason_line}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "amount", "reason_line"],
    },
}
