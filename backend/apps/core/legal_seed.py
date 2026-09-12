"""Legal page content.

Carried over from the frontend's hardcoded route files, with one substantive
correction: the tax wording is generated from ``Branch.prices_include_vat``
rather than asserted, so a published policy cannot contradict what the cart
actually charges.

`app/terms/page.tsx:47` currently says "All prices are in Nigerian Naira (₦)
and include applicable taxes", and `app/help/page.tsx:120` agrees — while
`CartSummary.tsx:23` adds 7.5% on top. Under the FCCPA 2018 that is a
misleading price representation, not a styling nit.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction


def _pricing_clause(branch: Any) -> str:
    rate = branch.vat_rate_bps / 100
    if branch.prices_include_vat:
        return (
            f"All prices are shown in Nigerian Naira (₦) and **include VAT at "
            f"{rate:g}%**. The price you see on the menu is the price you pay. "
            "Delivery, any service charge and any tip are shown separately "
            "before you confirm your order."
        )
    return (
        f"All prices are shown in Nigerian Naira (₦) **before VAT**. VAT at "
        f"{rate:g}% is added at checkout and itemised in your order summary, "
        "along with delivery, any service charge and any tip."
    )


def pages(branch: Any) -> list[dict[str, Any]]:
    return [
        {
            "slug": "terms",
            "title": "Terms of Service",
            "summary": "Initial version. Pricing clause generated from branch VAT policy.",
            "body": f"""## Terms of Service

### Using our service
By placing an order or booking a table with Kuyash Place you agree to these
terms. If you do not agree with them, please do not use the service.

### Pricing
{_pricing_clause(branch)}

Prices may change. The price that applies to your order is the one shown when
you place it — if anything changes while you are checking out, we will tell you
and ask you to confirm again rather than charge you a different amount.

### Orders
An order is accepted when the kitchen confirms it, not when you submit it. We
may decline an order — because an item has sold out, or we cannot deliver to
your address — and if you have already paid, we will refund you in full.

### Cancellation
You can cancel an order online until the kitchen starts preparing it. After
that, please call us and we will do what we can.

### Delivery
We deliver to the areas listed at checkout. Delivery times are estimates and
depend on how busy the kitchen is and on traffic.

### Payment
Card payments are handled by our payment provider. We never see or store your
card number.

### Contact
Questions about these terms: use the contact form or call the restaurant.
""",
        },
        {
            "slug": "privacy",
            "title": "Privacy Policy",
            "summary": "Initial version.",
            "body": """## Privacy Policy

### What we collect
Your name, email address, phone number and delivery address, so that we can
take and deliver your order. Your order history, so you can see it and reorder.
Nothing else is required.

### What we do not collect
We do not receive or store your card number, expiry date or security code.
Card details are entered on our payment provider's own page and never reach our
systems.

### Why we hold it
To fulfil your order, to contact you about it, and to meet our tax obligations.
We keep order records for seven years because we are required to; we do not
keep them longer than that.

### Marketing
Only if you asked for it. You can withdraw consent at any time from your
account settings or from any message we send.

### Your rights
Under the Nigeria Data Protection Regulation you can ask for a copy of your
data, correct it, or have it erased. Erasure anonymises your account: your
personal details are removed and the financial records we are obliged to keep
are no longer linked to a recognisable person.

### Sharing
With our payment provider, to take payment. With our delivery riders, so they
can find you. With nobody else.
""",
        },
        {
            "slug": "cookies",
            "title": "Cookie Policy",
            "summary": "Initial version.",
            "body": """## Cookie Policy

### What we use
A session cookie to keep you signed in, and a cookie to remember your basket
between visits. Both are necessary for the site to work.

### What we do not use
We do not use advertising or cross-site tracking cookies.

### Managing cookies
You can clear or block cookies in your browser. If you block the necessary
ones, you will not be able to stay signed in or keep a basket.
""",
        },
        {
            "slug": "refunds",
            "title": "Refund Policy",
            "summary": "Initial version.",
            "body": """## Refund Policy

### When we refund automatically
If we cannot fulfil your order after you have paid — the kitchen declines it,
or an item has sold out — you are refunded in full without having to ask.

### If something is wrong with your order
Tell us the same day. Depending on what happened we will refund the affected
items or the whole order.

### How long it takes
Refunds are sent back to the card or account you paid from. It can take a few
working days to appear on your statement; that part is your bank's timing, not
ours.

### Cash on delivery
Cash orders are refunded in cash or by transfer, arranged with you directly.
""",
        },
        {
            "slug": "accessibility",
            "title": "Accessibility Statement",
            "summary": "Initial version.",
            "body": """## Accessibility

### What we are aiming for
We want this site to be usable with a keyboard, with a screen reader, and at
whatever text size you need.

### Where we are
We are working towards WCAG 2.1 AA. We know some areas fall short of it today
and we are fixing them.

### If something does not work for you
Tell us through the contact form and we will treat it as a fault, not a
suggestion. If the site is blocking you, call the restaurant and we will take
your order over the phone.
""",
        },
    ]


@transaction.atomic
def seed_legal_pages(branch: Any, *, stdout: Any = None) -> int:
    """Publish the initial version of each policy page. Idempotent."""
    from apps.core.models import LegalPage

    created = 0
    for payload in pages(branch):
        _, made = LegalPage.objects.get_or_create(
            slug=payload["slug"],
            version=1,
            defaults={**{k: v for k, v in payload.items() if k != "slug"}, "published": True},
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} legal pages")
    return created
