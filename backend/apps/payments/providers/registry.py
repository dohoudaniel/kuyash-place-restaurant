"""Provider selection."""

from __future__ import annotations

from django.conf import settings

from apps.payments.models import Provider
from apps.payments.providers.base import PaymentProvider
from apps.payments.providers.dummy import DummyProvider
from apps.payments.providers.flutterwave import FlutterwaveProvider
from apps.payments.providers.paystack import PaystackProvider


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is requested but not configured."""


def get_provider(name: str) -> PaymentProvider:
    """Return a configured provider.

    Falls back to the simulated provider only when keys are absent **and**
    DEBUG is on. In production a missing key is an error, not a quiet
    downgrade to a provider that approves everything.
    """
    name = (name or settings.DEFAULT_PAYMENT_PROVIDER or "").lower()

    if name == Provider.PAYSTACK:
        key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if key:
            return PaystackProvider(key)
    elif name == Provider.FLUTTERWAVE:
        key = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        if key:
            return FlutterwaveProvider(key)
    elif name == "dummy" and settings.DEBUG:
        return DummyProvider()
    else:
        raise ProviderUnavailable(f"Unknown payment provider “{name}”.")

    if settings.DEBUG:
        return DummyProvider()
    raise ProviderUnavailable(
        f"{name} is not configured. Set its secret key before taking payments."
    )


def fallback_order(preferred: str) -> list[str]:
    """Providers to try, in order.

    Outages happen; a second provider is why we integrated two.
    """
    candidates = [preferred or settings.DEFAULT_PAYMENT_PROVIDER]
    for name in (Provider.PAYSTACK, Provider.FLUTTERWAVE):
        if name not in candidates:
            candidates.append(name)
    return [name for name in candidates if name]
