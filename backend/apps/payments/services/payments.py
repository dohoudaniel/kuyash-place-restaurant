"""Payment services.

The rule that governs this module: **an order becomes paid only when a
signature-verified webhook or a server-to-server verification says so, and the
amount matches.** The browser returning from the provider is a hint to verify,
never proof.

Two further rules earn their keep under concurrency, because a webhook, the
customer's return from checkout and the ten-minute reconciliation sweep can all
arrive at the same transaction at the same moment:

* **Settlement takes a row lock and re-reads.** An in-memory copy of a
  transaction says whatever it said when it was fetched; only the database knows
  whether someone else has settled it since.
* **A provider call never happens inside a database transaction.** A 20-second
  HTTP call with a row lock held is how a connection pool dies, and a refund that
  succeeds at the provider while our transaction rolls back is money gone with no
  record that it went.
"""

from __future__ import annotations

import datetime as dt
import logging
import secrets
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.exceptions import DomainError, IdempotencyConflict, PaymentFailed
from apps.orders.models import Order, OrderStatus, PaymentMethod, PaymentStatus
from apps.orders.services.state import transition
from apps.payments.models import (
    PaymentTransaction,
    Provider,
    Refund,
    RefundStatus,
    TransactionStatus,
)
from apps.payments.providers.base import RefundResult, VerifyResult
from apps.payments.providers.registry import ProviderUnavailable, fallback_order, get_provider

logger = logging.getLogger(__name__)

#: How long a provider's hosted checkout link is treated as still usable. Both
#: providers keep an initialised transaction alive far longer than this; the
#: window is deliberately short so an abandoned attempt does not pin a customer
#: to a stale link for the rest of the day.
CHECKOUT_LINK_TTL = dt.timedelta(minutes=30)

#: An attempt that has not reached a verdict yet.
IN_FLIGHT_STATUSES = (TransactionStatus.INITIALISED, TransactionStatus.PENDING)

#: Why a transaction failed, when the provider confirmed a different amount.
#: Named because the reconciliation sweep must never retry one of these: the
#: answer will not change, and each retry re-raises a security alert.
AMOUNT_MISMATCH_REASON = "amount_mismatch"


class PaymentAmountMismatch(DomainError):
    """The provider confirmed a different amount from the one we expected.

    This is a security event, not a rounding difference.
    """

    code = "payment_amount_mismatch"
    title = "Payment could not be confirmed"
    status_code = 402


def build_reference(payable: Any) -> str:
    """A unique provider reference per attempt, for an order or an enrolment.

    Per attempt, not per order: a customer who abandons a payment and retries
    needs a fresh reference, and providers reject reused ones. Which is why
    :func:`_start_payment` hands back a *live* attempt rather than minting one —
    see the note there.
    """
    return f"{payable.reference}-{secrets.token_hex(4)}"


# ──────────────────────────────────────────────────────────────────────────────
# Locking
# ──────────────────────────────────────────────────────────────────────────────


def _locked_transaction(record: PaymentTransaction) -> PaymentTransaction:
    """Re-read a transaction under a row lock.

    On SQLite this degrades to the surrounding transaction, which is sufficient
    for local development (ADR-015); CI runs the concurrency paths on Postgres.
    The *re-read* matters on both: the caller's instance may be minutes old.
    """
    queryset = PaymentTransaction.objects.filter(pk=record.pk)
    if settings.USING_POSTGRES:  # pragma: no cover - exercised in Postgres CI
        queryset = queryset.select_for_update()
    return queryset.get()


def _locked_order(order: Order) -> Order:
    """Re-read an order under a row lock. Same reasoning as above."""
    queryset = Order.objects.filter(pk=order.pk)
    if settings.USING_POSTGRES:  # pragma: no cover - exercised in Postgres CI
        queryset = queryset.select_for_update()
    return queryset.get()


def flag_for_review(record: PaymentTransaction, *, event: str, reason: str) -> None:
    """Mark settled money that a person has to look at, loudly.

    The alternative — the behaviour this replaces — was to notice the problem
    and return silently, which is how a second charge on an already-paid order
    became invisible to everyone except the customer's bank statement.
    """
    logger.critical(
        event,
        extra={
            "transaction": str(record.pk),
            "payable": record.payable_reference,
            "reason": reason,
        },
    )
    record.needs_review = True
    record.review_reason = reason[:255]
    record.save(update_fields=["needs_review", "review_reason", "updated_at"])


# ──────────────────────────────────────────────────────────────────────────────
# Starting a payment
# ──────────────────────────────────────────────────────────────────────────────


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
    return _start_payment(
        payable=order,
        link={"order": order},
        amount=order.grand_total,
        currency=order.currency,
        email=order.contact_email,
        callback_url=settings.PAYMENT_CALLBACK_URL,
        provider_name=provider_name,
        save_method=save_method,
    )


def initialise_enrolment_payment(*, enrolment: Any, provider_name: str = "") -> PaymentTransaction:
    """Start a card payment for a course enrolment (ACA-5).

    Same providers, same records, same verification and webhooks as an order.
    """
    from apps.academy.services import ensure_payable

    ensure_payable(enrolment)
    return _start_payment(
        payable=enrolment,
        link={"enrolment": enrolment},
        amount=enrolment.amount,
        currency=enrolment.currency,
        email=enrolment.email,
        callback_url=settings.ACADEMY_PAYMENT_CALLBACK_URL,
        provider_name=provider_name,
        save_method=False,
    )


def _live_attempt(link: dict[str, Any]) -> PaymentTransaction | None:
    """An attempt whose hosted checkout link is still usable, if there is one."""
    return (
        PaymentTransaction.objects.filter(
            **link,
            status__in=IN_FLIGHT_STATUSES,
            initialised_at__gt=timezone.now() - CHECKOUT_LINK_TTL,
        )
        .exclude(authorization_url="")
        .order_by("-initialised_at")
        .first()
    )


def _start_payment(
    *,
    payable: Any,
    link: dict[str, Any],
    amount: int,
    currency: str,
    email: str,
    callback_url: str,
    provider_name: str,
    save_method: bool,
) -> PaymentTransaction:
    """Return a usable checkout link, minting a new attempt only if there isn't one.

    **One payable, one live checkout link.** Two tabs, or a customer who taps
    "Pay" again while the first page loads, used to mint two references, both
    live at the provider. Both could be paid. The second settlement then found
    the order already paid and skipped silently, and because ``amount_paid`` is
    the order total rather than the sum of what settled, the second charge could
    not be refunded through the API at all.
    """
    live = _live_attempt(link)
    if live is not None:
        if provider_name and provider_name != live.provider:
            # Honouring this would put a second live checkout link on the same
            # bill, which is the whole failure being prevented here.
            raise PaymentFailed(
                "A payment for this is already in progress. "
                "Finish or abandon it before starting another."
            )
        if save_method and not live.save_method:
            # Consent given on the retry still counts.
            live.save_method = True
            live.save(update_fields=["save_method", "updated_at"])
        logger.info(
            "payment_initialise_reused",
            extra={"payable": payable.reference, "transaction": str(live.pk)},
        )
        return live

    kind = next(iter(link))
    last_error = ""
    for candidate in fallback_order(provider_name):
        try:
            provider = get_provider(candidate)
        except ProviderUnavailable as exc:
            last_error = str(exc)
            continue

        reference = build_reference(payable)
        record = PaymentTransaction.objects.create(
            **link,
            provider=candidate,
            our_reference=reference,
            amount=amount,
            currency=currency,
            status=TransactionStatus.INITIALISED,
            initialised_at=timezone.now(),
            save_method=save_method,
        )
        result = provider.initialise(
            amount_kobo=amount,
            email=email,
            reference=reference,
            callback_url=callback_url,
            currency=currency,
            metadata={kind: payable.reference},
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
            extra={"payable": payable.reference, "provider": candidate},
        )

    raise PaymentFailed(last_error or "No payment provider is available right now.")


# ──────────────────────────────────────────────────────────────────────────────
# Settling
# ──────────────────────────────────────────────────────────────────────────────


def _other_settled_transaction(record: PaymentTransaction) -> PaymentTransaction | None:
    """Another successful payment for the same thing — that is, a double charge."""
    payable: dict[str, Any] = (
        {"order_id": record.order_id} if record.order_id else {"enrolment_id": record.enrolment_id}
    )
    return (
        PaymentTransaction.objects.filter(status=TransactionStatus.SUCCESS, **payable)
        .exclude(pk=record.pk)
        .first()
    )


@transaction.atomic
def _settle(record: PaymentTransaction, result: VerifyResult, *, source: str) -> PaymentTransaction:
    """Apply a verified result to a transaction and its order.

    Atomic because the transaction record and the order status must move
    together: a settled payment against an unpaid order, or the reverse, is
    worse than either failing.

    The lock is the point of the first two lines. Between the provider answering
    and this write, a webhook or the sweep may have settled the same row; the
    instance in hand would not know.
    """
    record = _locked_transaction(record)
    if record.status == TransactionStatus.SUCCESS:
        return record

    duplicate = _other_settled_transaction(record)

    record.amount_verified = result.amount_kobo
    record.channel = result.channel[:40]
    record.authorization_code = result.authorization_code[:120]
    record.card_last4 = result.card_last4[:4]
    record.card_brand = result.card_brand[:30]
    record.card_exp_month = str(result.card_exp_month)[:2]
    record.card_exp_year = str(result.card_exp_year)[:4]
    if result.provider_reference:
        # The provider's own identifier for the transaction. Flutterwave refunds
        # address this, not the ``tx_ref`` we sent, so a refund raised against
        # the reference we minted is rejected. Only ever written here, on a
        # settled payment, so a retry still verifies by the reference we sent.
        record.provider_reference = result.provider_reference[:120]
    record.raw_response = result.raw
    record.verified_at = timezone.now()
    record.status = TransactionStatus.SUCCESS
    record.save()

    if duplicate is not None:
        flag_for_review(
            record,
            event="duplicate_payment_settled",
            reason=f"already settled by {duplicate.our_reference}; one of the two owes a refund",
        )

    order = record.order
    if order is not None:
        if order.status == OrderStatus.PENDING_PAYMENT:
            transition(order, OrderStatus.PAID, source=source)
        elif duplicate is None:
            # Expired by the sweep, or cancelled, and then paid. Money arrived
            # against an order nobody is going to cook.
            flag_for_review(
                record,
                event="payment_settled_against_unpayable_order",
                reason=f"order {order.reference} was {order.status} when the money arrived",
            )
    elif record.enrolment is not None:
        from apps.academy.services import confirm_payment

        confirm_payment(record.enrolment, record)

    _remember_card(record)
    return record


def _remember_card(record: PaymentTransaction) -> None:
    """Store the provider token, if the customer asked for it.

    Consent is required: a provider hands back a reusable token whether or not
    the customer wanted their card kept, and storing one regardless would be
    collecting a payment credential nobody agreed to.
    """
    user = record.order.user if record.order is not None else None
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
    the evidence of a suspicious attempt — and would hold a row lock across the
    provider's 20-second timeout.

    What *is* locked is the read at the top and the write in ``_settle``, so the
    webhook, the customer's return and the beat sweep cannot interleave into a
    double settlement.
    """
    with transaction.atomic():
        record = _locked_transaction(record)
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
                "payable": record.payable_reference,
                "expected": record.amount,
                "received": result.amount_kobo,
                "currency": result.currency,
            },
        )
        record.status = TransactionStatus.FAILED
        record.failure_reason = AMOUNT_MISMATCH_REASON
        record.amount_verified = result.amount_kobo
        record.raw_response = result.raw
        record.save()
        raise PaymentAmountMismatch(
            "The amount confirmed by the payment provider does not match this order."
        )

    return _settle(record, result, source=source)


def find_transaction(reference: str) -> PaymentTransaction | None:
    """Look a transaction up by either reference, without calling a provider.

    Separate from :func:`verify_by_reference` so a caller can check *who is
    asking* before spending an outbound provider call on them.
    """
    record = PaymentTransaction.objects.filter(our_reference=reference).first()
    if record is None:
        record = PaymentTransaction.objects.filter(provider_reference=reference).first()
    return record


def verify_by_reference(reference: str) -> PaymentTransaction | None:
    """Verify by our own reference — what the browser callback triggers.

    The outcome does not depend on anything the client sent beyond the
    reference: we ask the provider directly.
    """
    record = find_transaction(reference)
    if record is None:
        return None
    return verify_and_settle(record, source="customer")


# ──────────────────────────────────────────────────────────────────────────────
# Offline methods
# ──────────────────────────────────────────────────────────────────────────────


def _settled_total(order: Order) -> int:
    """What has actually been confirmed against this order, in kobo.

    The sum of settled transactions — not ``order.amount_paid``, which is set to
    the order total on the first settlement and therefore cannot tell you how
    much money arrived.
    """
    total = PaymentTransaction.objects.filter(
        order=order, status=TransactionStatus.SUCCESS
    ).aggregate(total=Sum("amount_verified"))["total"]
    return int(total or 0)


@transaction.atomic
def record_manual_payment(
    *,
    order: Order,
    amount_kobo: int,
    actor: Any = None,
    note: str = "",
    idempotency_key: str = "",
) -> PaymentTransaction:
    """Record a bank transfer confirmed by staff.

    Two things this refused to do before: compare the money to the bill, and
    survive a second click. A ₦5,000 transfer marked a ₦33,120 order paid in
    full, and doing it twice banked it twice.
    """
    if amount_kobo <= 0:
        raise PaymentFailed("A payment must be for a positive amount.")

    locked = _locked_order(order)
    key = idempotency_key[:64]
    if key:
        seen = PaymentTransaction.objects.filter(order=locked, idempotency_key=key).first()
        if seen is not None:
            return seen

    outstanding = locked.grand_total - _settled_total(locked)
    if outstanding <= 0:
        raise PaymentFailed("This order has already been paid in full.")
    if amount_kobo > outstanding:
        raise PaymentFailed("That is more than is outstanding on this order.")

    record = PaymentTransaction.objects.create(
        order=locked,
        provider=Provider.BANK_TRANSFER,
        our_reference=build_reference(locked),
        amount=locked.grand_total,
        amount_verified=amount_kobo,
        currency=locked.currency,
        status=TransactionStatus.SUCCESS,
        verified_at=timezone.now(),
        channel="bank",
        idempotency_key=key,
    )

    if amount_kobo < outstanding:
        # Part of the bill. The money is on the ledger, but the order is not
        # paid: saying it was would send the kitchen cooking for money that
        # never arrived, and would let the balance be refunded.
        logger.warning(
            "partial_manual_payment",
            extra={
                "order": locked.reference,
                "received": amount_kobo,
                "outstanding": outstanding,
            },
        )
        return record

    if locked.status == OrderStatus.PENDING_PAYMENT:
        transition(locked, OrderStatus.PAID, actor=actor, source="staff", note=note)
    return record


# ──────────────────────────────────────────────────────────────────────────────
# Refunds
# ──────────────────────────────────────────────────────────────────────────────


def refund_order(
    *,
    order: Order,
    amount_kobo: int | None = None,
    reason: str = "",
    actor: Any = None,
    idempotency_key: str = "",
) -> Refund:
    """Refund an order, fully or partially.

    Three steps, and the shape of them is the fix: a short transaction that
    reserves the refund under a lock and **commits**, then the provider call
    outside any transaction, then a short transaction that records what happened.

    What it replaces held a single transaction open across a 20-second provider
    call, and read the over-refund guard without a lock — so two managers
    double-clicking Refund both passed the guard and both refunded.

    Reverses the promo redemption and restores the customer's allowance via the
    ``order_status_changed`` receiver.
    """
    refund, record, created = _open_refund(
        order=order,
        amount_kobo=amount_kobo,
        reason=reason,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    if not created:
        # An identical refund already ran to completion under this key.
        return refund

    outcome: RefundResult | None = None
    if record is not None and record.provider in {Provider.PAYSTACK, Provider.FLUTTERWAVE}:
        provider = get_provider(record.provider)
        outcome = provider.refund(
            record.provider_reference or record.our_reference, amount_kobo=refund.amount
        )

    return _close_refund(refund=refund, order=order, outcome=outcome, reason=reason, actor=actor)


@transaction.atomic
def _open_refund(
    *,
    order: Order,
    amount_kobo: int | None,
    reason: str,
    actor: Any,
    idempotency_key: str,
) -> tuple[Refund, PaymentTransaction | None, bool]:
    """Reserve the refund under a lock, and commit before anyone is called."""
    locked = _locked_order(order)
    key = idempotency_key[:64]
    if key:
        seen = Refund.objects.filter(order=locked, idempotency_key=key).first()
        if seen is not None:
            if seen.status == RefundStatus.PENDING:
                raise IdempotencyConflict(
                    "A refund for this order is already being processed. Please wait a moment."
                )
            return seen, None, False

    amount = locked.amount_paid if amount_kobo is None else amount_kobo
    if amount <= 0:
        raise PaymentFailed("There is nothing to refund on this order.")

    # Pending rows count towards the total. The row the *other* manager's click
    # committed a moment ago is exactly what has to stop this one.
    already = Refund.objects.filter(
        order=locked, status__in=[RefundStatus.SUCCESS, RefundStatus.PENDING]
    ).aggregate(total=Sum("amount"))["total"]
    if int(already or 0) + amount > locked.amount_paid:
        raise PaymentFailed("That would refund more than was paid.")

    record = PaymentTransaction.objects.filter(
        order=locked, status=TransactionStatus.SUCCESS
    ).first()
    refund = Refund.objects.create(
        transaction=record,
        order=locked,
        amount=amount,
        reason=reason,
        status=RefundStatus.PENDING,
        idempotency_key=key,
        initiated_by=actor if actor is not None and getattr(actor, "pk", None) else None,
    )
    return refund, record, True


@transaction.atomic
def _close_refund(
    *,
    refund: Refund,
    order: Order,
    outcome: RefundResult | None,
    reason: str,
    actor: Any,
) -> Refund:
    """Record what the provider said, and move the order if the money went back."""
    locked = _locked_order(order)

    if outcome is None:
        # Cash and bank transfer are reconciled offline; the record is the ledger.
        refund.status = RefundStatus.SUCCESS
    else:
        refund.status = RefundStatus.SUCCESS if outcome.ok else RefundStatus.FAILED
        refund.provider_reference = outcome.provider_reference[:120]
        refund.raw_response = outcome.raw
        if not outcome.ok:
            refund.reason = f"{reason} (provider error: {outcome.error})"[:1000]
    refund.save()

    if refund.status != RefundStatus.SUCCESS:
        return refund

    refunded = Refund.objects.filter(order=locked, status=RefundStatus.SUCCESS).aggregate(
        total=Sum("amount")
    )["total"]
    fully = int(refunded or 0) >= locked.amount_paid
    locked.payment_status = PaymentStatus.REFUNDED if fully else PaymentStatus.PARTIALLY_REFUNDED
    locked.save(update_fields=["payment_status", "updated_at"])
    if fully and locked.status != OrderStatus.REFUNDED:
        transition(locked, OrderStatus.REFUNDED, actor=actor, source="staff", note=reason)

    from apps.carts.serializers import money
    from apps.notifications.services import queue_templated_email

    queue_templated_email(
        template_key="refund_issued",
        recipient=locked.contact_email,
        context={
            "name": locked.contact_name,
            "reference": locked.reference,
            "amount": money(refund.amount, locked.currency)["display"],
            "reason_line": f"Reason: {reason}" if reason else "",
        },
    )
    return refund
