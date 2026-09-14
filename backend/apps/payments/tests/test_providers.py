"""Provider adapters.

Each provider reports in its own units and shapes; these tests pin the
translation so a change in one cannot quietly alter what we charge.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import requests
import responses

from apps.payments.providers.base import parse_money_json
from apps.payments.providers.dummy import DummyProvider
from apps.payments.providers.flutterwave import FlutterwaveProvider
from apps.payments.providers.paystack import PaystackProvider
from apps.payments.providers.registry import ProviderUnavailable, fallback_order, get_provider

FLW = "https://api.flutterwave.com/v3"
PS = "https://api.paystack.co"


# ── JSON parsing ──────────────────────────────────────────────────────────────


def test_provider_json_parses_amounts_as_decimal_not_float() -> None:
    """A provider amount must never become a binary float on the way in."""
    parsed = parse_money_json('{"amount": 25500.55}')
    assert isinstance(parsed["amount"], Decimal)
    assert parsed["amount"] == Decimal("25500.55")


def test_provider_json_handles_bytes_and_empty_bodies() -> None:
    assert parse_money_json(b'{"a": 1}') == {"a": 1}
    assert parse_money_json("") == {}


# ── Paystack ──────────────────────────────────────────────────────────────────


@responses.activate
def test_paystack_reports_kobo_unchanged() -> None:
    """Paystack already speaks kobo, so no conversion is applied."""
    responses.add(
        responses.GET,
        f"{PS}/transaction/verify/ref-1",
        json={
            "status": True,
            "data": {
                "status": "success",
                "amount": 3_312_000,
                "currency": "NGN",
                "authorization": {},
            },
        },
        status=200,
    )
    result = PaystackProvider("sk_test").verify("ref-1")
    assert result.amount_kobo == 3_312_000
    assert result.succeeded is True


@responses.activate
def test_paystack_maps_unknown_states_to_pending() -> None:
    responses.add(
        responses.GET,
        f"{PS}/transaction/verify/ref-1",
        json={
            "status": True,
            "data": {"status": "some_new_state", "amount": 1, "authorization": {}},
        },
        status=200,
    )
    assert PaystackProvider("sk_test").verify("ref-1").status == "pending"


@responses.activate
def test_paystack_verify_reports_a_refusal_as_failed() -> None:
    """Paystack answers ``status: false`` for a reference it won't verify."""
    responses.add(
        responses.GET,
        f"{PS}/transaction/verify/ref-1",
        json={"status": False, "message": "Transaction reference not found"},
        status=400,
    )
    result = PaystackProvider("sk_test").verify("ref-1")
    assert result.status == "failed"
    assert result.succeeded is False
    assert "not found" in result.message


@responses.activate
def test_paystack_network_errors_become_pending_not_failed() -> None:
    """A timeout means "we do not know", not "the customer did not pay"."""
    responses.add(
        responses.GET,
        f"{PS}/transaction/verify/ref-1",
        body=requests.ConnectionError("timeout"),
    )
    assert PaystackProvider("sk_test").verify("ref-1").status == "pending"


@responses.activate
def test_paystack_initialise_handles_a_network_error() -> None:
    responses.add(
        responses.POST, f"{PS}/transaction/initialize", body=requests.ConnectionError("down")
    )
    result = PaystackProvider("sk_test").initialise(
        amount_kobo=1, email="a@b.com", reference="r", callback_url="https://x"
    )
    assert result.ok is False
    assert "ConnectionError" in result.error


@responses.activate
def test_paystack_initialise_reports_a_rejection() -> None:
    responses.add(
        responses.POST,
        f"{PS}/transaction/initialize",
        json={"status": False, "message": "Invalid key"},
        status=401,
    )
    result = PaystackProvider("sk_test").initialise(
        amount_kobo=1, email="a@b.com", reference="r", callback_url="https://x"
    )
    assert result.ok is False and "Invalid key" in result.error


@responses.activate
def test_paystack_refund_paths() -> None:
    responses.add(
        responses.POST, f"{PS}/refund", json={"status": True, "data": {"id": 7}}, status=200
    )
    assert PaystackProvider("sk_test").refund("ref-1", 1000).ok is True

    responses.reset()
    responses.add(
        responses.POST, f"{PS}/refund", json={"status": False, "message": "nope"}, status=400
    )
    assert PaystackProvider("sk_test").refund("ref-1").ok is False

    responses.reset()
    responses.add(responses.POST, f"{PS}/refund", body=requests.ConnectionError("x"))
    assert PaystackProvider("sk_test").refund("ref-1").ok is False


def test_paystack_without_a_key_cannot_verify_a_webhook() -> None:
    assert PaystackProvider("").verify_webhook(b"{}", {}) is False


# ── Flutterwave ───────────────────────────────────────────────────────────────


@responses.activate
def test_flutterwave_naira_is_converted_to_kobo_exactly() -> None:
    """The unit difference that would otherwise be a 100x error."""
    responses.add(
        responses.GET,
        f"{FLW}/transactions/verify_by_reference",
        json={
            "status": "success",
            "data": {
                "status": "successful",
                "amount": 25500.55,
                "currency": "NGN",
                "card": {"last_4digits": "4242", "type": "visa", "expiry": "12/29"},
            },
        },
        status=200,
    )
    result = FlutterwaveProvider("k", "h").verify("ref-1")
    assert result.amount_kobo == 2_550_055
    assert result.card_last4 == "4242"
    assert result.card_exp_month == "12"


@responses.activate
def test_flutterwave_initialise_sends_naira() -> None:
    import json

    responses.add(
        responses.POST,
        f"{FLW}/payments",
        json={"status": "success", "data": {"link": "https://pay"}},
        status=200,
    )
    FlutterwaveProvider("k", "h").initialise(
        amount_kobo=2_550_055, email="a@b.com", reference="r", callback_url="https://x"
    )
    sent = json.loads(responses.calls[0].request.body)
    assert sent["amount"] == "25500.55"  # major units, exact


@responses.activate
def test_flutterwave_failure_paths() -> None:
    responses.add(responses.POST, f"{FLW}/payments", body=requests.ConnectionError("x"))
    assert (
        FlutterwaveProvider("k", "h")
        .initialise(amount_kobo=1, email="a@b.com", reference="r", callback_url="https://x")
        .ok
        is False
    )

    responses.reset()
    responses.add(
        responses.POST, f"{FLW}/payments", json={"status": "error", "message": "bad"}, status=400
    )
    assert (
        FlutterwaveProvider("k", "h")
        .initialise(amount_kobo=1, email="a@b.com", reference="r", callback_url="https://x")
        .ok
        is False
    )

    responses.reset()
    responses.add(
        responses.GET, f"{FLW}/transactions/verify_by_reference", body=requests.ConnectionError("x")
    )
    assert FlutterwaveProvider("k", "h").verify("r").status == "pending"

    responses.reset()
    responses.add(
        responses.GET,
        f"{FLW}/transactions/verify_by_reference",
        json={"status": "error", "message": "no"},
        status=404,
    )
    assert FlutterwaveProvider("k", "h").verify("r").status == "failed"


@responses.activate
def test_flutterwave_refund_paths() -> None:
    responses.add(
        responses.POST,
        f"{FLW}/transactions/ref-1/refund",
        json={"status": "success", "data": {"id": 3}},
        status=200,
    )
    assert FlutterwaveProvider("k", "h").refund("ref-1", 1000).ok is True

    responses.reset()
    responses.add(
        responses.POST,
        f"{FLW}/transactions/ref-1/refund",
        json={"status": "error", "message": "no"},
        status=400,
    )
    assert FlutterwaveProvider("k", "h").refund("ref-1").ok is False

    responses.reset()
    responses.add(
        responses.POST, f"{FLW}/transactions/ref-1/refund", body=requests.ConnectionError("x")
    )
    assert FlutterwaveProvider("k", "h").refund("ref-1").ok is False


@pytest.mark.parametrize("amount", [None, ""])
def test_flutterwave_missing_amount_is_zero_kobo(amount) -> None:  # type: ignore[no-untyped-def]
    """No amount must read as nothing paid — never as the order total."""
    from apps.payments.providers.flutterwave import _to_kobo

    assert _to_kobo(amount) == 0


def test_flutterwave_webhook_hash_comparison() -> None:
    provider = FlutterwaveProvider("k", "secret-hash")
    assert provider.verify_webhook(b"{}", {"verif-hash": "secret-hash"}) is True
    assert provider.verify_webhook(b"{}", {"verif-hash": "wrong"}) is False
    assert provider.verify_webhook(b"{}", {}) is False
    assert FlutterwaveProvider("k", "").verify_webhook(b"{}", {"verif-hash": "x"}) is False


def test_flutterwave_event_extraction() -> None:
    event_id, event_type, reference = FlutterwaveProvider("k", "h").extract_event(
        {"event": "charge.completed", "data": {"id": 12, "tx_ref": "KYS-X-1"}}
    )
    assert (event_id, event_type, reference) == ("12", "charge.completed", "KYS-X-1")


# ── Registry ──────────────────────────────────────────────────────────────────


def test_configured_providers_are_returned(settings) -> None:  # type: ignore[no-untyped-def]
    settings.PAYSTACK_SECRET_KEY = "sk"
    settings.FLUTTERWAVE_SECRET_KEY = "fk"
    assert isinstance(get_provider("paystack"), PaystackProvider)
    assert isinstance(get_provider("flutterwave"), FlutterwaveProvider)


def test_an_unconfigured_provider_fails_in_production(settings) -> None:  # type: ignore[no-untyped-def]
    """A missing key must never downgrade to a provider that approves everything."""
    settings.PAYSTACK_SECRET_KEY = ""
    settings.DEBUG = False
    with pytest.raises(ProviderUnavailable, match="not configured"):
        get_provider("paystack")


def test_the_simulator_is_only_available_in_debug(settings) -> None:  # type: ignore[no-untyped-def]
    settings.PAYSTACK_SECRET_KEY = ""
    settings.DEBUG = True
    assert isinstance(get_provider("paystack"), DummyProvider)

    settings.DEBUG = False
    with pytest.raises(ProviderUnavailable):
        get_provider("dummy")


def test_the_simulator_can_be_asked_for_by_name_in_debug(settings) -> None:  # type: ignore[no-untyped-def]
    settings.DEBUG = True
    assert isinstance(get_provider("dummy"), DummyProvider)


def test_an_unknown_provider_name_is_refused(settings) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ProviderUnavailable, match="Unknown payment provider"):
        get_provider("bitcoin")


def test_fallback_order_prefers_the_requested_provider(settings) -> None:  # type: ignore[no-untyped-def]
    assert fallback_order("flutterwave")[0] == "flutterwave"
    assert "paystack" in fallback_order("flutterwave")


# ── Simulator ─────────────────────────────────────────────────────────────────


def test_the_simulator_never_trusts_a_webhook() -> None:
    """Even in development, a simulated webhook must not settle an order."""
    assert DummyProvider().verify_webhook(b"{}", {"any": "header"}) is False


@pytest.mark.django_db
def test_the_simulator_round_trips() -> None:
    provider = DummyProvider()
    init = provider.initialise(
        amount_kobo=1000, email="a@b.com", reference="r", callback_url="https://x"
    )
    assert init.ok and "simulated=1" in init.authorization_url
    assert provider.verify("r").succeeded is True
    assert provider.refund("r").ok is True
    assert provider.extract_event({"id": "1", "event": "e", "reference": "r"}) == ("1", "e", "r")

    failing = DummyProvider(succeed=False)
    assert failing.verify("r").succeeded is False


# ── Simulated provider ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_the_simulated_provider_settles_a_payment_end_to_end(order, settings) -> None:  # type: ignore[no-untyped-def]
    """In development the dummy provider must let the whole checkout be walked.

    It used to verify every payment as ₦0, which settlement correctly treats as
    an amount mismatch — so no simulated card payment could ever succeed.
    """
    from apps.payments.models import TransactionStatus
    from apps.payments.services.payments import initialise_payment, verify_and_settle

    settings.DEBUG = True
    settings.PAYSTACK_SECRET_KEY = ""
    settings.FLUTTERWAVE_SECRET_KEY = ""

    record = initialise_payment(order=order)
    settled = verify_and_settle(record)

    assert settled.status == TransactionStatus.SUCCESS
    assert settled.amount_verified == order.grand_total
    order.refresh_from_db()
    assert order.is_paid


@pytest.mark.django_db
def test_the_simulated_provider_reports_nothing_for_an_unknown_reference(db) -> None:  # type: ignore[no-untyped-def]
    from apps.payments.providers.dummy import DummyProvider

    result = DummyProvider().verify("no-such-reference")
    assert result.amount_kobo == 0
