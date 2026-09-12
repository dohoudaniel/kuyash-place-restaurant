"""Failure records must survive the exception that reports them.

An attempt we could not complete is evidence — of an outage, a misconfigured
key, or an attack. Rolling it back with the exception destroys exactly the
record an operator needs.
"""

from __future__ import annotations

import pytest
import requests
import responses

from apps.common.exceptions import PaymentFailed
from apps.payments.models import PaymentTransaction, TransactionStatus
from apps.payments.services.payments import initialise_payment

pytestmark = pytest.mark.django_db


@responses.activate
def test_a_total_provider_outage_still_records_the_attempts(  # type: ignore[no-untyped-def]
    order, paystack_keys, flutterwave_keys
) -> None:
    responses.add(
        responses.POST,
        "https://api.paystack.co/transaction/initialize",
        body=requests.ConnectionError("paystack down"),
    )
    responses.add(
        responses.POST,
        "https://api.flutterwave.com/v3/payments",
        body=requests.ConnectionError("flutterwave down"),
    )

    with pytest.raises(PaymentFailed):
        initialise_payment(order=order)

    attempts = PaymentTransaction.objects.filter(order=order)
    assert attempts.count() == 2, "both failed attempts must be on record"
    assert {a.provider for a in attempts} == {"paystack", "flutterwave"}
    assert all(a.status == TransactionStatus.FAILED for a in attempts)
    assert all("ConnectionError" in a.failure_reason for a in attempts)


def test_no_configured_provider_reports_clearly(order, settings) -> None:  # type: ignore[no-untyped-def]
    settings.PAYSTACK_SECRET_KEY = ""
    settings.FLUTTERWAVE_SECRET_KEY = ""
    settings.DEBUG = False

    with pytest.raises(PaymentFailed, match="not configured"):
        initialise_payment(order=order)
