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
        return VerifyResult(
            status="success" if self.succeed else "failed",
            amount_kobo=0,
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
