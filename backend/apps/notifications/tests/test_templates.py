"""Email templates.

The governing principle: a template problem must degrade the *wording*, never
suppress the message. A customer who paid and hears nothing is a support call;
a customer who gets slightly off-brand prose is fine.
"""

from __future__ import annotations

import pytest

from apps.notifications.models import EmailTemplate, Notification
from apps.notifications.services import (
    TemplateRenderError,
    queue_templated_email,
    render_template,
)
from apps.notifications.templates_data import DEFAULT_TEMPLATES

pytestmark = pytest.mark.django_db


def test_built_in_wording_is_used_when_no_row_exists() -> None:
    subject, text, html = render_template(
        "order_confirmation",
        {
            "name": "Ada",
            "reference": "KYS-AAA111",
            "total": "₦21,800.00",
            "fulfilment_line": "For collection.",
            "tracking_url": "https://x/orders/KYS-AAA111",
        },
    )
    assert subject == "Order KYS-AAA111 confirmed"
    assert "Ada" in text
    assert "₦21,800.00" in text
    assert html == ""


def test_a_database_row_overrides_the_built_in() -> None:
    EmailTemplate.objects.create(
        key="order_delivered",
        subject="Your Kuyash order landed",
        text_body="Hi {name}, order {reference} is with you.",
    )
    subject, text, _ = render_template(
        "order_delivered", {"name": "Ada", "reference": "KYS-AAA111"}
    )
    assert subject == "Your Kuyash order landed"
    assert text == "Hi Ada, order KYS-AAA111 is with you."


def test_an_inactive_row_falls_back_to_the_built_in() -> None:
    EmailTemplate.objects.create(
        key="order_delivered", subject="Custom", text_body="Custom", is_active=False
    )
    subject, _, _ = render_template("order_delivered", {"name": "A", "reference": "R"})
    assert subject == DEFAULT_TEMPLATES["order_delivered"]["subject"].format(reference="R")


def test_a_template_with_a_bad_placeholder_falls_back_not_fails() -> None:
    """An admin typo must not stop an order confirmation going out."""
    EmailTemplate.objects.create(
        key="order_delivered",
        subject="Order {reference}",
        text_body="Hello {nonexistent_placeholder}",
    )
    subject, text, _ = render_template(
        "order_delivered", {"name": "Ada", "reference": "KYS-AAA111"}
    )
    assert "KYS-AAA111" in subject or "KYS-AAA111" in text
    assert "nonexistent_placeholder" not in text


def test_an_unknown_template_key_raises() -> None:
    with pytest.raises(TemplateRenderError):
        render_template("no_such_template", {})


def test_queueing_an_unknown_template_returns_none_rather_than_crashing() -> None:
    assert queue_templated_email(template_key="no_such_template", recipient="a@b.com") is None


def test_an_empty_recipient_is_skipped() -> None:
    assert queue_templated_email(template_key="order_delivered", recipient="") is None


def test_html_is_sent_as_an_alternative_part(  # type: ignore[no-untyped-def]
    mailoutbox, django_capture_on_commit_callbacks
) -> None:
    EmailTemplate.objects.create(
        key="order_delivered",
        subject="Order {reference}",
        text_body="Plain text for {reference}",
        html_body="<p>HTML for {reference}</p>",
    )
    with django_capture_on_commit_callbacks(execute=True):
        queue_templated_email(
            template_key="order_delivered",
            recipient="ada@example.com",
            context={"reference": "KYS-AAA111", "name": "Ada"},
        )
    message = mailoutbox[0]
    assert message.body == "Plain text for KYS-AAA111"
    assert message.alternatives[0][0] == "<p>HTML for KYS-AAA111</p>"
    assert message.alternatives[0][1] == "text/html"


def test_the_outbox_records_the_rendered_body(  # type: ignore[no-untyped-def]
    mailoutbox, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        queue_templated_email(
            template_key="order_delivered",
            recipient="ada@example.com",
            context={"name": "Ada", "reference": "KYS-AAA111"},
        )
    record = Notification.objects.get(template_key="order_delivered")
    assert "KYS-AAA111" in record.body
    assert record.status == "sent"


@pytest.mark.parametrize("key", sorted(DEFAULT_TEMPLATES))
def test_every_built_in_template_renders_with_its_declared_context(key: str) -> None:
    """A template that lists a placeholder it cannot render is a latent outage."""
    payload = DEFAULT_TEMPLATES[key]
    context = {name: f"<{name}>" for name in payload["available_context"]}
    subject, text, _ = render_template(key, context)
    assert subject and text


@pytest.mark.parametrize("key", sorted(DEFAULT_TEMPLATES))
def test_every_built_in_template_declares_the_placeholders_it_uses(key: str) -> None:
    """Catch a placeholder used in the body but missing from available_context."""
    import string

    payload = DEFAULT_TEMPLATES[key]
    declared = set(payload["available_context"])
    used = {
        field
        for body in (payload["subject"], payload["text_body"])
        for _, field, _, _ in string.Formatter().parse(body)
        if field
    }
    assert used <= declared, f"{key} uses undeclared placeholders: {used - declared}"
