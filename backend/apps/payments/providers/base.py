"""The payment provider interface.

Adding a third provider is a new class, not a new branch in the order service.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


def parse_money_json(raw: bytes | str) -> Any:
    """Parse provider JSON with **Decimal**, never float.

    Providers report amounts in major units (Flutterwave sends ``25500.55``).
    ``json.loads`` would turn that into a binary float before we ever saw it,
    which is precisely the defect the money module exists to prevent. Parsing
    floats as :class:`Decimal` keeps the value exact end to end.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw or "{}", parse_float=Decimal)


@dataclass(frozen=True, slots=True)
class InitResult:
    """Outcome of asking a provider to start a payment."""

    ok: bool
    authorization_url: str = ""
    provider_reference: str = ""
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """What a provider says actually happened.

    ``amount_kobo`` is always minor units, whatever the provider reports in.
    """

    status: str  # success | failed | pending | abandoned
    amount_kobo: int = 0
    currency: str = "NGN"
    channel: str = ""
    authorization_code: str = ""
    card_last4: str = ""
    card_brand: str = ""
    card_exp_month: str = ""
    card_exp_year: str = ""
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True, slots=True)
class RefundResult:
    ok: bool
    provider_reference: str = ""
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PaymentProvider(Protocol):
    """Every provider implements exactly this."""

    name: str

    def initialise(
        self,
        *,
        amount_kobo: int,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> InitResult: ...

    def verify(self, reference: str) -> VerifyResult: ...

    def refund(self, reference: str, amount_kobo: int | None = None) -> RefundResult: ...

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...

    def extract_event(self, payload: Mapping[str, Any]) -> tuple[str, str, str]:
        """Return ``(event_id, event_type, provider_reference)`` from a webhook."""
        ...  # pragma: no cover - protocol stub
