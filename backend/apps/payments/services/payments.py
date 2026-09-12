"""Payment services.

The rule that governs this module: **an order becomes paid only when a
signature-verified webhook or a server-to-server verification says so, and the
amount matches.** The browser returning from the provider is a hint to verify,
never proof.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import DomainError, PaymentFailed
from apps.orders.models import Order, OrderStatus, PaymentMethod, PaymentStatus
from apps.orders.services.state import transition
from apps.payments.models import (
    PaymentTransaction,
    Provider,
    Refund,
    RefundStatus,
    TransactionStatus,
)
from apps.payments.providers.base import VerifyResult
from apps.payments.providers.registry import ProviderUnavailable, fallback_order, get_provider

logger = logging.getLogger(__name__)


class PaymentAmountMismatch(DomainError):
    """The provider confirmed a different amount from the one we expected.

    This is a security event, not a rounding difference.
    """

    code = "payment_amount_mismatch"
    title = "Payment could not be confirmed"
    status_code = 402


def build_reference(order: Order) -> str:
    """A unique provider reference per attempt.

    Per attempt, not per order: a customer who abandons a payment and retries
    needs a fresh reference, and providers reject reused ones.
    """
    return f"{order.reference}-{secrets.token_hex(4)}"


def initialise_payment(
    *, order: Order, provider_name: str = "", save_method: bool = False
) -> PaymentTransaction:
    """Start a payment and return the transaction holding the checkout URL.

    Deliberately **not** atomic. Each provider attempt writes its own record and
    there is no invariant spanning them; wrapping the loop in a transaction
    would roll back every failure record when the final raise fires, destroying
    the evidence of an outage, a bad key, or an attack. Same reasoning as
    :func:`verify_and_settle`.
    """
    if order.payment_method == PaymentMethod.CASH:
        raise PaymentFailed("Cash orders are settled on delivery, not online.")
    if order.is_paid:
        raise PaymentFailed("This order has already been paid.")

    last_error = ""
    for candidate in fallback_order(provider_name):
        try:
            provider = get_provider(candidate)
        except ProviderUnavailable as exc:
            last_error = str(exc)
            continue

        reference = build_reference(order)
        record = PaymentTransaction.objects.create(
            order=order,
            provider=candidate,
            our_reference=reference,
            amount=order.grand_total,
            currency=order.currency,
            status=TransactionStatus.INITIALISED,
            initialised_at=timezone.now(),
            save_method=save_method,
        )
        result = provider.initialise(
            amount_kobo=order.grand_total,
            email=order.contact_email,
            reference=reference,
            callback_url=settings.PAYMENT_CALLBACK_URL,
            metadata={"order": order.reference},
        )
        if result.ok:
            record.status = TransactionStatus.PENDING
            record.authorization_url = result.authorization_url[:500]
            record.provider_reference = result.provider_reference
            record.raw_response = result.raw
            record.save()
            return record

        record.status = TransactionStatus.FAILED
        record.failure_reason = result.error[:255]
        record.save()
        last_error = result.error
        logger.warning(
            "payment_initialise_failed",
            extra={"order": order.reference, "provider": candidate},
        )

    raise PaymentFailed(last_error or "No payment provider is available right now.")


@transaction.atomic
def _settle(record: PaymentTransaction, result: VerifyResult, *, source: str) -> PaymentTransaction:
    """Apply a verified result to a transaction and its order.

    Atomic because the transaction record and the order status must move
    together: a settled payment against an unpaid order, or the reverse, is
    worse than either failing.
    """
    record.amount_verified = result.amount_kobo
    record.channel = result.channel[:40]
    record.authorization_code = result.authorization_code[:120]
    record.card_last4 = result.card_last4[:4]
    record.card_brand = result.card_brand[:30]
    record.card_exp_month = str(result.card_exp_month)[:2]
    record.card_exp_year = str(result.card_exp_year)[:4]
    record.raw_response = result.raw
    record.verified_at = timezone.now()
    record.status = TransactionStatus.SUCCESS
    record.save()

    order = record.order
    if order.status == OrderStatus.PENDING_PAYMENT:
        transition(order, OrderStatus.PAID, source=source)

    _remember_card(record)
    return record


def _remember_card(record: PaymentTransaction) -> None:
    """Store the provider token, if the customer asked for it.

    Consent is required: a provider hands back a reusable token whether or not
    the customer wanted their card kept, and storing one regardless would be
    collecting a payment credential nobody agreed to.
    """
    user = record.order.user
    if not (record.save_method and user and record.authorization_code):
        return

    from apps.payments.models import SavedPaymentMethod

    method, created = SavedPaymentMethod.objects.get_or_create(
        user=user,
        authorization_code=record.authorization_code,
        defaults={
            "provider": record.provider,
            "card_last4": record.card_last4,
            "card_brand": record.card_brand,
            "card_exp_month": record.card_exp_month,
            "card_exp_year": record.card_exp_year,
            "is_default": not SavedPaymentMethod.objects.filter(user=user, is_active=True).exists(),
        },
    )
    method.last_used_at = timezone.now()
    method.is_active = True
    method.save(update_fields=["last_used_at", "is_active", "updated_at"])
    if created:
        logger.info("payment_method_saved", extra={"user": str(user.pk)})


def verify_and_settle(record: PaymentTransaction, *, source: str = "system") -> PaymentTransaction:
    """Ask the provider what happened, then act on the answer.

    An amount mismatch leaves the order **unpaid** and raises. Paying ₦100 for
    a ₦33,120 order must never produce a paid order.

    Deliberately **not** atomic as a whole. Only settlement needs a transaction
    (see :func:`_settle`); wrapping the entire function would roll back the very
    record that documents a failed or mismatched payment when it raises, losing
    the evidence of a suspicious attempt.
    """
    if record.status == TransactionStatus.SUCCESS:
        return record

    provider = get_provider(record.provider)
    result = provider.verify(record.provider_reference or record.our_reference)

    if result.status == "pending":
        record.status = TransactionStatus.PENDING
        record.failure_reason = result.message[:255]
        record.save(update_fields=["status", "failure_reason", "updated_at"])
        return record

    if not result.succeeded:
        record.status = (
            TransactionStatus.ABANDONED
            if result.status == "abandoned"
            else TransactionStatus.FAILED
        )
        record.failure_reason = (result.message or "Payment was not completed.")[:255]
        record.raw_response = result.raw
        record.save()
        return record

    if result.amount_kobo != record.amount or result.currency != record.currency:
        logger.critical(
            "payment_amount_mismatch",
            extra={
                "transaction": str(record.pk),
                "order": record.order.reference,
                "expected": record.amount,
                "received": result.amount_kobo,
                "currency": result.currency,
            },
        )
        record.status = TransactionStatus.FAILED
        record.failure_reason = "amount_mismatch"
        record.amount_verified = result.amount_kobo
        record.raw_response = result.raw
        record.save()
        raise PaymentAmountMismatch(
            "The amount confirmed by the payment provider does not match this order."
        )

    return _settle(record, result, source=source)


def verify_by_reference(reference: str) -> PaymentTransaction | None:
    """Verify by our own reference — what the browser callback triggers.

    The outcome does not depend on anything the client sent beyond the
    reference: we ask the provider directly.
    """
    record = PaymentTransaction.objects.filter(our_reference=reference).first()
    if record is None:
        record = PaymentTransaction.objects.filter(provider_reference=reference).first()
    if record is None:
        return None
    return verify_and_settle(record, source="customer")


# ──────────────────────────────────────────────────────────────────────────────
# Offline methods
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def record_manual_payment(
    *, order: Order, amount_kobo: int, actor: Any = None, note: str = ""
) -> PaymentTransaction:
    """Record a bank transfer confirmed by staff."""
    record = PaymentTransaction.objects.create(
        order=order,
        provider=Provider.BANK_TRANSFER,
        our_reference=build_reference(order),
        amount=order.grand_total,
        amount_verified=amount_kobo,
        currency=order.currency,
        status=TransactionStatus.SUCCESS,
        verified_at=timezone.now(),
        channel="bank",
    )
    if order.status == OrderStatus.PENDING_PAYMENT:
        transition(order, OrderStatus.PAID, actor=actor, source="staff", note=note)
    return record


# ──────────────────────────────────────────────────────────────────────────────
# Refunds
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def refund_order(
    *, order: Order, amount_kobo: int | None = None, reason: str = "", actor: Any = None
) -> Refund:
    """Refund an order, fully or partially.

    Reverses the promo redemption and restores the customer's allowance via the
    ``order_status_changed`` receiver.
    """
    amount = order.amount_paid if amount_kobo is None else amount_kobo
    if amount <= 0:
        raise PaymentFailed("There is nothing to refund on this order.")
    already = sum(
        refund.amount for refund in Refund.objects.filter(order=order, status=RefundStatus.SUCCESS)
    )
    if already + amount > order.amount_paid:
        raise PaymentFailed("That would refund more than was paid.")

    record = PaymentTransaction.objects.filter(
        order=order, status=TransactionStatus.SUCCESS
    ).first()
    refund = Refund.objects.create(
        transaction=record,
        order=order,
        amount=amount,
        reason=reason,
        initiated_by=actor if actor is not None and getattr(actor, "pk", None) else None,
    )

    if record is not None and record.provider in {Provider.PAYSTACK, Provider.FLUTTERWAVE}:
        provider = get_provider(record.provider)
        result = provider.refund(
            record.provider_reference or record.our_reference, amount_kobo=amount
        )
        refund.status = RefundStatus.SUCCESS if result.ok else RefundStatus.FAILED
        refund.provider_reference = result.provider_reference[:120]
        refund.raw_response = result.raw
        if not result.ok:
            refund.reason = f"{reason} (provider error: {result.error})"[:1000]
        refund.save()
    else:
        # Cash and bank transfer are reconciled offline; the record is the ledger.
        refund.status = RefundStatus.SUCCESS
        refund.save()

    if refund.status == RefundStatus.SUCCESS:
        fully = (already + amount) >= order.amount_paid
        order.payment_status = PaymentStatus.REFUNDED if fully else PaymentStatus.PARTIALLY_REFUNDED
        order.save(update_fields=["payment_status", "updated_at"])
        if fully and order.status != OrderStatus.REFUNDED:
            transition(order, OrderStatus.REFUNDED, actor=actor, source="staff", note=reason)

        from apps.carts.serializers import money
        from apps.notifications.services import queue_templated_email

        queue_templated_email(
            template_key="refund_issued",
            recipient=order.contact_email,
            context={
                "name": order.contact_name,
                "reference": order.reference,
                "amount": money(amount, order.currency)["display"],
                "reason_line": f"Reason: {reason}" if reason else "",
            },
        )

    return refund
