"""Paystack.

Hosted checkout: the customer enters card details on Paystack's page, not ours.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Mapping
from typing import Any

import requests
from django.conf import settings

from apps.payments.providers.base import (
    InitResult,
    RefundResult,
    VerifyResult,
    parse_money_json,
)

logger = logging.getLogger(__name__)

API_ROOT = "https://api.paystack.co"
TIMEOUT = 20

#: Paystack transaction states mapped onto ours.
_STATUS = {
    "success": "success",
    "failed": "failed",
    "abandoned": "abandoned",
    "ongoing": "pending",
    "pending": "pending",
    "processing": "pending",
    "queued": "pending",
    "reversed": "failed",
}


class PaystackProvider:
    name = "paystack"

    def __init__(self, secret_key: str | None = None) -> None:
        self.secret_key = secret_key or getattr(settings, "PAYSTACK_SECRET_KEY", "")

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{API_ROOT}{path}", json=payload, headers=self._headers(), timeout=TIMEOUT
        )
        return parse_money_json(response.content)

    def _get(self, path: str) -> dict[str, Any]:
        response = requests.get(f"{API_ROOT}{path}", headers=self._headers(), timeout=TIMEOUT)
        return parse_money_json(response.content)

    # ── Interface ─────────────────────────────────────────────────────────────

    def initialise(
        self,
        *,
        amount_kobo: int,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> InitResult:
        """Start a payment. Paystack takes the amount in kobo already."""
        try:
            body = self._post(
                "/transaction/initialize",
                {
                    "amount": amount_kobo,
                    "email": email,
                    "reference": reference,
                    "callback_url": callback_url,
                    "currency": "NGN",
                    "metadata": dict(metadata or {}),
                },
            )
        except requests.RequestException as exc:
            logger.warning("paystack_initialise_failed", extra={"reference": reference})
            return InitResult(ok=False, error=f"{exc.__class__.__name__}: {exc}")

        if not body.get("status"):
            return InitResult(ok=False, error=str(body.get("message", "Initialisation failed.")))

        data = body.get("data") or {}
        return InitResult(
            ok=True,
            authorization_url=data.get("authorization_url", ""),
            provider_reference=data.get("reference", reference),
            raw=body,
        )

    def verify(self, reference: str) -> VerifyResult:
        """Ask Paystack what actually happened. Server to server, always."""
        try:
            body = self._get(f"/transaction/verify/{reference}")
        except requests.RequestException as exc:
            return VerifyResult(status="pending", message=f"{exc.__class__.__name__}: {exc}")

        if not body.get("status"):
            return VerifyResult(status="failed", message=str(body.get("message", "")))

        data = body.get("data") or {}
        authorization = data.get("authorization") or {}
        return VerifyResult(
            status=_STATUS.get(str(data.get("status", "")).lower(), "pending"),
            # Paystack reports kobo; coerce through int() in case it arrives as Decimal.
            amount_kobo=int(data.get("amount") or 0),
            currency=data.get("currency", "NGN"),
            channel=data.get("channel", ""),
            authorization_code=authorization.get("authorization_code", ""),
            card_last4=authorization.get("last4", ""),
            card_brand=authorization.get("brand", ""),
            card_exp_month=authorization.get("exp_month", ""),
            card_exp_year=authorization.get("exp_year", ""),
            message=str(data.get("gateway_response", "")),
            raw=body,
        )

    def refund(self, reference: str, amount_kobo: int | None = None) -> RefundResult:
        payload: dict[str, Any] = {"transaction": reference}
        if amount_kobo is not None:
            payload["amount"] = amount_kobo
        try:
            body = self._post("/refund", payload)
        except requests.RequestException as exc:
            return RefundResult(ok=False, error=f"{exc.__class__.__name__}: {exc}")

        if not body.get("status"):
            return RefundResult(ok=False, error=str(body.get("message", "Refund failed.")))
        data = body.get("data") or {}
        return RefundResult(ok=True, provider_reference=str(data.get("id", "")), raw=body)

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """HMAC-SHA512 over the **raw body**, compared in constant time.

        Verifying a re-serialised dict instead of the raw bytes would let an
        attacker slip through on any formatting difference.
        """
        if not self.secret_key:
            return False
        expected = hmac.new(self.secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
        supplied = headers.get("x-paystack-signature", "") or headers.get(
            "X-Paystack-Signature", ""
        )
        return bool(supplied) and hmac.compare_digest(expected, supplied)

    def extract_event(self, payload: Mapping[str, Any]) -> tuple[str, str, str]:
        data = payload.get("data") or {}
        event_id = str(data.get("id") or payload.get("id") or data.get("reference", ""))
        return event_id, str(payload.get("event", "")), str(data.get("reference", ""))
