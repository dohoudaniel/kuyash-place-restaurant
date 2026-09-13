"""A provider that never talks to the network.

Used when no provider keys are configured — local development and tests — so a
developer can walk the whole checkout without an account. It is deliberately
**not** selectable in production: ``get_provider`` refuses it when DEBUG is off.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.payments.providers.base import InitResult, RefundResult, VerifyResult


class DummyProvider:
    name = "dummy"

    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed
        self.initialised: list[dict[str, Any]] = []

    def initialise(
        self,
        *,
        amount_kobo: int,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> InitResult:
        self.initialised.append({"reference": reference, "amount": amount_kobo})
        return InitResult(
            ok=True,
            authorization_url=f"{callback_url}?reference={reference}&simulated=1",
            provider_reference=reference,
            raw={"simulated": True, "amount": amount_kobo},
        )

    def verify(self, reference: str) -> VerifyResult:
        """Report the amount that was actually asked for.

        A real provider tells us what it charged, and settlement refuses any
        payment whose amount differs from the order's. The simulation used to
        report ₦0, so every simulated card payment in development tripped that
        security check and failed — the whole checkout could not be walked.
        """
        from django.db.models import Q

        from apps.payments.models import PaymentTransaction

        record = PaymentTransaction.objects.filter(
            Q(our_reference=reference) | Q(provider_reference=reference)
        ).first()
        return VerifyResult(
            status="success" if self.succeed else "failed",
            amount_kobo=record.amount if record else 0,
            currency=record.currency if record else "NGN",
            channel="simulated",
            message="simulated",
            raw={"simulated": True},
        )

    def refund(self, reference: str, amount_kobo: int | None = None) -> RefundResult:
        return RefundResult(ok=True, provider_reference=f"sim-refund-{reference}")

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        return False  # never trust a webhook in simulation

    def extract_event(self, payload: Mapping[str, Any]) -> tuple[str, str, str]:
        return (
            str(payload.get("id", "")),
            str(payload.get("event", "")),
            str(payload.get("reference", "")),
        )
