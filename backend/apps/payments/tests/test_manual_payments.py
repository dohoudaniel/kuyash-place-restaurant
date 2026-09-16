"""Staff-recorded bank transfers are money, and are checked like money.

``record_manual_payment`` never compared the amount received to the bill, so a
₦5,000 transfer against a ₦33,120 order marked it paid in full — and doing it
twice banked it twice.
"""

from __future__ import annotations

import pytest

from apps.common.exceptions import PaymentFailed
from apps.orders.models import OrderStatus, PaymentStatus
from apps.payments.models import PaymentTransaction, TransactionStatus
from apps.payments.services.payments import record_manual_payment

pytestmark = pytest.mark.django_db


def test_a_short_transfer_does_not_mark_the_order_paid(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    part = order.grand_total // 4

    record = record_manual_payment(order=order, amount_kobo=part, actor=manager_user)

    assert record.status == TransactionStatus.SUCCESS
    assert record.amount_verified == part
    order.refresh_from_db()
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.payment_status != PaymentStatus.PAID


def test_the_balance_completes_the_payment(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    part = order.grand_total // 4
    record_manual_payment(order=order, amount_kobo=part, actor=manager_user)

    order.refresh_from_db()
    record_manual_payment(order=order, amount_kobo=order.grand_total - part, actor=manager_user)

    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
    assert PaymentTransaction.objects.filter(order=order).count() == 2


def test_more_than_the_bill_is_refused(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PaymentFailed, match="more than is outstanding"):
        record_manual_payment(order=order, amount_kobo=order.grand_total + 1, actor=manager_user)

    assert not PaymentTransaction.objects.filter(order=order).exists()


def test_recording_the_same_transfer_twice_banks_it_once(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    """The double-clicked admin action."""
    first = record_manual_payment(
        order=order, amount_kobo=order.grand_total, actor=manager_user, idempotency_key="teller-1"
    )
    second = record_manual_payment(
        order=order, amount_kobo=order.grand_total, actor=manager_user, idempotency_key="teller-1"
    )

    assert second.pk == first.pk
    assert PaymentTransaction.objects.filter(order=order).count() == 1


def test_a_second_transfer_against_a_paid_order_is_refused(order, manager_user) -> None:  # type: ignore[no-untyped-def]
    """Without a key, the amount check is what stops it."""
    record_manual_payment(order=order, amount_kobo=order.grand_total, actor=manager_user)

    order.refresh_from_db()
    with pytest.raises(PaymentFailed, match="already been paid in full"):
        record_manual_payment(order=order, amount_kobo=order.grand_total, actor=manager_user)


@pytest.mark.parametrize("amount", [0, -100])
def test_a_payment_must_be_for_a_positive_amount(order, manager_user, amount) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PaymentFailed, match="positive amount"):
        record_manual_payment(order=order, amount_kobo=amount, actor=manager_user)
