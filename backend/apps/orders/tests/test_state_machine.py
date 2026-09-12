"""Order state machine."""

from __future__ import annotations

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.common.exceptions import IllegalTransition
from apps.orders.models import Order, OrderStatus, OrderStatusEvent
from apps.orders.services.state import TRANSITIONS, can_transition, timeline, transition

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(db, branch):  # type: ignore[no-untyped-def]
    return Order.objects.create(
        branch=branch,
        payment_method="card",
        grand_total=1_000_000,
        guest_email="ada@example.com",
    )


@pytest.mark.parametrize(
    ("frm", "to", "legal"),
    [
        (OrderStatus.PENDING_PAYMENT, OrderStatus.PAID, True),
        (OrderStatus.PENDING_PAYMENT, OrderStatus.DELIVERED, False),  # no skipping
        (OrderStatus.PAID, OrderStatus.CONFIRMED, True),
        (OrderStatus.DELIVERED, OrderStatus.PREPARING, False),  # no going back
        (OrderStatus.REFUNDED, OrderStatus.PAID, False),  # terminal
        (OrderStatus.EXPIRED, OrderStatus.PAID, False),  # terminal
        (OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY, True),
    ],
)
def test_transition_legality(order: Order, frm: str, to: str, legal: bool) -> None:
    Order.objects.filter(pk=order.pk).update(status=frm)
    order.refresh_from_db()
    if legal:
        assert transition(order, to).status == to
    else:
        with pytest.raises(IllegalTransition):
            transition(order, to)


def test_every_status_has_a_transition_entry() -> None:
    """A status missing from the table would be silently unreachable and unexitable."""
    assert set(TRANSITIONS) == set(OrderStatus.values)


def test_a_transition_writes_an_append_only_event(order: Order) -> None:
    transition(order, OrderStatus.PAID, note="webhook verified")
    event = OrderStatusEvent.objects.get(order=order)
    assert event.from_status == OrderStatus.PENDING_PAYMENT
    assert event.to_status == OrderStatus.PAID
    assert event.note == "webhook verified"


def test_timestamps_are_stamped_on_arrival(order: Order) -> None:
    transition(order, OrderStatus.PAID)
    transition(order, OrderStatus.CONFIRMED)
    order.refresh_from_db()
    assert order.accepted_at is not None
    assert order.ready_at is None


def test_kitchen_may_accept_but_not_refund(order: Order, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    assert can_transition(kitchen_user, OrderStatus.CONFIRMED) is True
    assert can_transition(kitchen_user, OrderStatus.REFUNDED) is False


def test_a_manager_may_refund(order: Order, manager_user) -> None:  # type: ignore[no-untyped-def]
    assert can_transition(manager_user, OrderStatus.REFUNDED) is True


def test_a_customer_may_not_advance_a_ticket(order: Order, verified_user) -> None:  # type: ignore[no-untyped-def]
    transition(order, OrderStatus.PAID)
    with pytest.raises(PermissionDenied):
        transition(order, OrderStatus.CONFIRMED, actor=verified_user)


def test_the_system_may_act_without_an_actor(order: Order) -> None:
    """Webhooks and beat tasks have no user."""
    assert can_transition(None, OrderStatus.REFUNDED) is True


def test_cancelling_records_the_reason(order: Order) -> None:
    transition(order, OrderStatus.CANCELLED, note="Customer changed their mind")
    order.refresh_from_db()
    assert order.cancellation_reason == "Customer changed their mind"


def test_concurrent_accepts_produce_one_transition(order: Order, kitchen_user) -> None:  # type: ignore[no-untyped-def]
    """Two staff tapping Accept at once must not double-advance the ticket."""
    transition(order, OrderStatus.PAID)

    succeeded = 0
    for _ in range(2):
        try:
            transition(order, OrderStatus.CONFIRMED, actor=kitchen_user)
            succeeded += 1
        except IllegalTransition:
            pass

    assert succeeded == 1
    assert (
        OrderStatusEvent.objects.filter(order=order, to_status=OrderStatus.CONFIRMED).count() == 1
    )


def test_timeline_marks_reached_steps(order: Order) -> None:
    transition(order, OrderStatus.PAID)
    transition(order, OrderStatus.CONFIRMED)
    steps = {step["status"]: step["reached"] for step in timeline(order)}
    assert steps[OrderStatus.PAID] is True
    assert steps[OrderStatus.CONFIRMED] is True
    assert steps[OrderStatus.DELIVERED] is False


def test_timeline_omits_delivery_for_pickup(branch) -> None:  # type: ignore[no-untyped-def]
    pickup = Order.objects.create(
        branch=branch,
        payment_method="cash",
        fulfilment_type="pickup",
        grand_total=1,
    )
    statuses = [step["status"] for step in timeline(pickup)]
    assert OrderStatus.OUT_FOR_DELIVERY not in statuses
    assert OrderStatus.DELIVERED in statuses


def test_timeline_appends_a_terminal_status(order: Order) -> None:
    transition(order, OrderStatus.CANCELLED)
    assert timeline(order)[-1]["status"] == OrderStatus.CANCELLED


def test_riders_may_dispatch_and_deliver(order: Order, db) -> None:  # type: ignore[no-untyped-def]
    from django.contrib.auth.models import Group

    from apps.accounts.models import User

    rider = User.objects.create_user(
        email="rider@kuyashplace.com", password="correct-horse-battery-staple"
    )
    rider.groups.add(Group.objects.get_or_create(name="riders")[0])

    assert can_transition(rider, OrderStatus.OUT_FOR_DELIVERY) is True
    assert can_transition(rider, OrderStatus.DELIVERED) is True
    assert can_transition(rider, OrderStatus.CONFIRMED) is False  # not the kitchen's job
    assert can_transition(rider, OrderStatus.REFUNDED) is False


def test_a_customer_may_drive_no_transition(order: Order, verified_user) -> None:  # type: ignore[no-untyped-def]
    for status in (
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.DELIVERED,
        OrderStatus.REFUNDED,
        OrderStatus.PAID,
    ):
        assert can_transition(verified_user, status) is False


def test_event_actor_role_is_recorded(order: Order, kitchen_user, manager_user) -> None:  # type: ignore[no-untyped-def]
    """The audit trail names who acted, not just what changed."""
    transition(order, OrderStatus.PAID)
    transition(order, OrderStatus.CONFIRMED, actor=kitchen_user)
    assert OrderStatusEvent.objects.get(
        order=order, to_status=OrderStatus.CONFIRMED
    ).actor_role == ("kitchen")

    transition(order, OrderStatus.REFUNDED, actor=manager_user)
    assert OrderStatusEvent.objects.get(order=order, to_status=OrderStatus.REFUNDED).actor_role == (
        "managers"
    )


def test_a_superuser_is_recorded_as_admin(order: Order, db) -> None:  # type: ignore[no-untyped-def]
    from apps.accounts.models import User

    admin = User.objects.create_superuser(
        email="root@kuyashplace.com", password="correct-horse-battery-staple"
    )
    transition(order, OrderStatus.PAID, actor=admin)
    assert OrderStatusEvent.objects.get(order=order).actor_role == "admin"
