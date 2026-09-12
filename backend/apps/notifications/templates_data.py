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
    "contact_received": {
        "description": "Acknowledgement sent when the contact form is used.",
        "subject": "We have your message — {reference}",
        "text_body": (
            "Hello {name},\n\n"
            "Thank you for getting in touch. We have your message and will reply "
            "as soon as we can.\n\n"
            "Reference: {reference}\n"
            "Subject:   {subject}" + SIGN_OFF
        ),
        "available_context": ["name", "reference", "subject"],
    },
    "contact_internal": {
        "description": "Alert to the team when the contact form is used.",
        "subject": "[Support] {reference} — {reason}: {subject}",
        "text_body": (
            "Reference: {reference}\n"
            "From:      {name} <{email}>\n"
            "Reason:    {reason}\n"
            "Subject:   {subject}\n\n"
            "{message}\n"
        ),
        "available_context": ["reference", "name", "email", "reason", "subject", "message"],
    },
    "ticket_reply": {
        "description": "Sent when staff reply to a support ticket.",
        "subject": "Re: {subject} ({reference})",
        "text_body": ("Hello {name},\n\n{body}\n\nReference: {reference}" + SIGN_OFF),
        "available_context": ["name", "reference", "subject", "body"],
    },
    "catering_enquiry_received": {
        "description": "Acknowledgement sent to a catering enquirer.",
        "subject": "We have your catering enquiry — {reference}",
        "text_body": (
            "Hello {name},\n\n"
            "Thank you for your catering enquiry. A member of our team will be in "
            "touch by {respond_by}.\n\n"
            "Reference: {reference}\n"
            "Guests:    {guest_count}\n"
            "{indicative_line}" + SIGN_OFF
        ),
        "available_context": [
            "name",
            "reference",
            "guest_count",
            "indicative_line",
            "respond_by",
        ],
    },
    "catering_enquiry_internal": {
        "description": "Alert to the team when a catering enquiry arrives.",
        "subject": "[Catering] {reference} — {guest_count} guests, respond by {respond_by}",
        "text_body": (
            "A catering enquiry needs a response by {respond_by}.\n\n"
            "Reference:  {reference}\n"
            "Name:       {name}\n"
            "Email:      {email}\n"
            "Phone:      {phone}\n"
            "Guests:     {guest_count}\n"
            "Event type: {event_type}\n"
            "Date:       {event_date}\n"
            "Venue:      {venue}\n\n"
            "Message:\n{message}\n"
        ),
        "available_context": [
            "reference",
            "name",
            "email",
            "phone",
            "guest_count",
            "event_type",
            "event_date",
            "venue",
            "message",
            "respond_by",
        ],
    },
    "reservation_confirmed": {
        "description": "Sent when a table is booked.",
        "subject": "Table booked — {date} at {time}",
        "text_body": (
            "Hello {name},\n\n"
            "Your table is booked. We look forward to seeing you.\n\n"
            "Reference: {reference}\n"
            "When:      {date} at {time}\n"
            "Guests:    {party_size}\n"
            "Area:      {area}\n\n"
            "View or cancel your booking: {manage_url}" + SIGN_OFF
        ),
        "available_context": [
            "name",
            "reference",
            "date",
            "time",
            "party_size",
            "area",
            "manage_url",
        ],
    },
    "reservation_rescheduled": {
        "description": "Sent when a booking is moved.",
        "subject": "Booking moved — {date} at {time}",
        "text_body": (
            "Hello {name},\n\n"
            "Your booking has been moved.\n\n"
            "Reference: {reference}\n"
            "New time:  {date} at {time}\n"
            "Guests:    {party_size}\n"
            "Area:      {area}\n\n"
            "View or cancel your booking: {manage_url}" + SIGN_OFF
        ),
        "available_context": [
            "name",
            "reference",
            "date",
            "time",
            "party_size",
            "area",
            "manage_url",
        ],
    },
    "reservation_cancelled": {
        "description": "Sent when a booking is cancelled.",
        "subject": "Booking cancelled — {reference}",
        "text_body": (
            "Hello {name},\n\n"
            "Your booking for {date} at {time} has been cancelled.\n"
            "We hope to see you another time.\n\n"
            "Reference: {reference}" + SIGN_OFF
        ),
        "available_context": [
            "name",
            "reference",
            "date",
            "time",
            "party_size",
            "area",
            "manage_url",
        ],
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
