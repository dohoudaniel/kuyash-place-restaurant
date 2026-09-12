"""Flutterwave.

Note the unit difference from Paystack: Flutterwave reports amounts in **major
units** (naira), so every amount is converted to kobo through ``Decimal``.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

from apps.common.money import naira_to_kobo
from apps.payments.providers.base import (
    InitResult,
    RefundResult,
    VerifyResult,
    parse_money_json,
)

logger = logging.getLogger(__name__)

API_ROOT = "https://api.flutterwave.com/v3"
TIMEOUT = 20

_STATUS = {
    "successful": "success",
    "success": "success",
    "failed": "failed",
    "cancelled": "abandoned",
    "pending": "pending",
}


def _to_kobo(value: Any) -> int:
    """Convert a Flutterwave major-unit amount to kobo, exactly.

    The response was parsed with ``parse_float=Decimal``, so ``value`` is
    already exact; ``str()`` keeps it that way through ``naira_to_kobo``, which
    refuses binary floats outright.
    """
    if value in (None, ""):
        return 0
    if isinstance(value, Decimal | int | str):
        return naira_to_kobo(str(value))
    return naira_to_kobo(str(value))  # pragma: no cover - defensive


class FlutterwaveProvider:
    name = "flutterwave"

    def __init__(self, secret_key: str | None = None, webhook_hash: str | None = None) -> None:
        self.secret_key = secret_key or getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        self.webhook_hash = webhook_hash or getattr(settings, "FLUTTERWAVE_WEBHOOK_SECRET_HASH", "")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialise(
        self,
        *,
        amount_kobo: int,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> InitResult:
        # Flutterwave takes naira, so convert from our canonical kobo.
        amount_naira = (Decimal(amount_kobo) / 100).quantize(Decimal("0.01"))
        try:
            response = requests.post(
                f"{API_ROOT}/payments",
                json={
                    "tx_ref": reference,
                    "amount": str(amount_naira),
                    "currency": "NGN",
                    "redirect_url": callback_url,
                    "customer": {"email": email},
                    "meta": dict(metadata or {}),
                },
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            body = parse_money_json(response.content)
        except requests.RequestException as exc:
            logger.warning("flutterwave_initialise_failed", extra={"reference": reference})
            return InitResult(ok=False, error=f"{exc.__class__.__name__}: {exc}")

        if str(body.get("status", "")).lower() != "success":
            return InitResult(ok=False, error=str(body.get("message", "Initialisation failed.")))
        data = body.get("data") or {}
        return InitResult(
            ok=True,
            authorization_url=data.get("link", ""),
            provider_reference=reference,
            raw=body,
        )

    def verify(self, reference: str) -> VerifyResult:
        try:
            response = requests.get(
                f"{API_ROOT}/transactions/verify_by_reference",
                params={"tx_ref": reference},
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            body = parse_money_json(response.content)
        except requests.RequestException as exc:
            return VerifyResult(status="pending", message=f"{exc.__class__.__name__}: {exc}")

        if str(body.get("status", "")).lower() != "success":
            return VerifyResult(status="failed", message=str(body.get("message", "")))

        data = body.get("data") or {}
        card = data.get("card") or {}
        return VerifyResult(
            status=_STATUS.get(str(data.get("status", "")).lower(), "pending"),
            amount_kobo=_to_kobo(data.get("amount")),
            currency=data.get("currency", "NGN"),
            channel=data.get("payment_type", ""),
            authorization_code=str(data.get("id", "")),
            card_last4=card.get("last_4digits", ""),
            card_brand=card.get("type", ""),
            card_exp_month=str(card.get("expiry", "")).split("/")[0] if card.get("expiry") else "",
            card_exp_year=str(card.get("expiry", "")).split("/")[-1] if card.get("expiry") else "",
            message=str(data.get("processor_response", "")),
            raw=body,
        )

    def refund(self, reference: str, amount_kobo: int | None = None) -> RefundResult:
        payload: dict[str, Any] = {}
        if amount_kobo is not None:
            payload["amount"] = str((Decimal(amount_kobo) / 100).quantize(Decimal("0.01")))
        try:
            response = requests.post(
                f"{API_ROOT}/transactions/{reference}/refund",
                json=payload,
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            body = parse_money_json(response.content)
        except requests.RequestException as exc:
            return RefundResult(ok=False, error=f"{exc.__class__.__name__}: {exc}")

        if str(body.get("status", "")).lower() != "success":
            return RefundResult(ok=False, error=str(body.get("message", "Refund failed.")))
        return RefundResult(
            ok=True, provider_reference=str((body.get("data") or {}).get("id", "")), raw=body
        )

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Flutterwave sends a shared secret in ``verif-hash``.

        Weaker than an HMAC over the body, so the amount is always re-verified
        against the provider API before anything is settled.
        """
        if not self.webhook_hash:
            return False
        supplied = headers.get("verif-hash", "") or headers.get("Verif-Hash", "")
        return bool(supplied) and hmac.compare_digest(self.webhook_hash, supplied)

    def extract_event(self, payload: Mapping[str, Any]) -> tuple[str, str, str]:
        data = payload.get("data") or payload
        event_id = str(data.get("id") or data.get("tx_ref", ""))
        return event_id, str(payload.get("event", "charge.completed")), str(data.get("tx_ref", ""))
