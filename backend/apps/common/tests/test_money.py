"""Money tests.

This module carries the 100% coverage requirement (docs/TESTING.md §1). Every
branch that can change what a customer is charged is exercised here.
"""

from __future__ import annotations

import ast
import pathlib
from decimal import Decimal

import pytest

from apps.common.money import (
    BPS_DIVISOR,
    Money,
    MoneyError,
    add_vat,
    allocate,
    apply_bps,
    compute_total,
    extract_vat,
    format_money,
    format_money_ascii,
    kobo_to_naira,
    naira_to_kobo,
    round_half_up,
    vat_for,
)

# ──────────────────────────────────────────────────────────────────────────────
# VAT
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("gross", "expected_vat"),
    [
        (0, 0),
        (1, 0),  # sub-kobo rounds to zero, never negative
        (100, 7),  # ₦1.00 → 6.97…k → ROUND_HALF_UP → 7k
        (10_750, 750),  # exactly 7.5% of the net ₦100
        (3_312_000, 231_070),  # the worked example in docs/PAYMENTS.md §7.1
    ],
)
def test_vat_inclusive_extraction(gross: int, expected_vat: int) -> None:
    assert extract_vat(gross, rate_bps=750) == expected_vat


@pytest.mark.parametrize(
    ("net", "expected_vat"),
    [(0, 0), (100, 8), (10_000, 750), (3_080_930, 231_070)],
)
def test_vat_exclusive_addition(net: int, expected_vat: int) -> None:
    assert add_vat(net, rate_bps=750) == expected_vat


def test_vat_round_trip_is_stable() -> None:
    """Adding VAT to a net amount and extracting it again returns the same VAT."""
    net = 3_080_930
    vat = add_vat(net, 750)
    assert extract_vat(net + vat, 750) == vat


def test_zero_rate_yields_no_vat() -> None:
    assert extract_vat(1_000_000, rate_bps=0) == 0
    assert add_vat(1_000_000, rate_bps=0) == 0


def test_vat_for_dispatches_on_policy() -> None:
    assert vat_for(10_750, 750, inclusive=True) == extract_vat(10_750, 750)
    assert vat_for(10_000, 750, inclusive=False) == add_vat(10_000, 750)


def test_vat_rejects_negative_amount() -> None:
    with pytest.raises(MoneyError, match="must not be negative"):
        extract_vat(-1, 750)
    with pytest.raises(MoneyError, match="must not be negative"):
        add_vat(-1, 750)


def test_vat_rejects_impossible_rate() -> None:
    with pytest.raises(MoneyError, match="must not exceed"):
        extract_vat(100, BPS_DIVISOR + 1)
    with pytest.raises(MoneyError, match="must not be negative"):
        extract_vat(100, -1)


def test_vat_is_summed_per_line_not_applied_to_subtotal() -> None:
    """A zero-rated line must not attract VAT via the order subtotal.

    Applying the rate to a combined subtotal would silently tax the zero-rated
    line — the reason tax is computed per line and then summed.
    """
    standard_line, zero_rated_line = 100_000, 100_000
    per_line = extract_vat(standard_line, 750) + 0
    on_subtotal = extract_vat(standard_line + zero_rated_line, 750)
    assert per_line == extract_vat(100_000, 750)
    assert per_line != on_subtotal


# ──────────────────────────────────────────────────────────────────────────────
# Proportions
# ──────────────────────────────────────────────────────────────────────────────


def test_percentage_discount_respects_cap_to_the_kobo() -> None:
    assert apply_bps(10_000_000, 1000, cap=500_000) == 500_000


def test_percentage_discount_under_cap_is_untouched() -> None:
    assert apply_bps(1_000_000, 1000, cap=500_000) == 100_000


def test_apply_bps_without_cap() -> None:
    assert apply_bps(3_680_000, 1000) == 368_000


def test_apply_bps_validates_inputs() -> None:
    with pytest.raises(MoneyError):
        apply_bps(-1, 1000)
    with pytest.raises(MoneyError):
        apply_bps(1000, -1)
    with pytest.raises(MoneyError):
        apply_bps(1000, 1000, cap=-1)


# ──────────────────────────────────────────────────────────────────────────────
# Rounding and totals
# ──────────────────────────────────────────────────────────────────────────────


def test_rounding_applied_once_not_accumulated() -> None:
    """Three lines of ₦3.33 total ₦9.99, never ₦10.00."""
    assert compute_total([333, 333, 333]) == 999


def test_compute_total_rejects_non_integers() -> None:
    with pytest.raises(MoneyError):
        compute_total([100, "200"])  # type: ignore[list-item]


def test_round_half_up_ties_away_from_zero() -> None:
    assert round_half_up(Decimal("0.5")) == 1
    assert round_half_up(Decimal("1.5")) == 2
    assert round_half_up(Decimal("-0.5")) == -1
    assert round_half_up(Decimal("2.4")) == 2


def test_round_half_up_requires_decimal() -> None:
    with pytest.raises(MoneyError, match="expects a Decimal"):
        round_half_up(1.5)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────────
# Allocation
# ──────────────────────────────────────────────────────────────────────────────


def test_allocate_sums_exactly_to_the_whole() -> None:
    parts = allocate(1000, [1, 1, 1])
    assert sum(parts) == 1000
    assert parts == [334, 333, 333]


def test_allocate_weights_proportionally() -> None:
    parts = allocate(1000, [3, 1])
    assert sum(parts) == 1000
    assert parts == [750, 250]


def test_allocate_handles_zero_weights() -> None:
    assert allocate(500, [0, 0]) == [500, 0]


def test_allocate_handles_negative_amount() -> None:
    """Refund allocation: the parts must still sum exactly."""
    parts = allocate(-1000, [1, 1, 1])
    assert sum(parts) == -1000


def test_allocate_rejects_empty_weights() -> None:
    with pytest.raises(MoneyError, match="at least one weight"):
        allocate(100, [])


def test_allocate_rejects_negative_weight() -> None:
    with pytest.raises(MoneyError):
        allocate(100, [1, -1])


# ──────────────────────────────────────────────────────────────────────────────
# Conversion and formatting
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [("14.90", 1490), (15, 1500), (Decimal("0.01"), 1), ("0", 0), ("1234.567", 123457)],
)
def test_naira_to_kobo(value: object, expected: int) -> None:
    assert naira_to_kobo(value) == expected  # type: ignore[arg-type]


def test_naira_to_kobo_refuses_binary_fractions() -> None:
    """The defect this module exists to prevent: 14.90 is not exactly representable."""
    with pytest.raises(MoneyError, match="not exactly representable"):
        naira_to_kobo(14.90)  # type: ignore[arg-type]


def test_naira_to_kobo_refuses_bool() -> None:
    with pytest.raises(MoneyError):
        naira_to_kobo(True)  # type: ignore[arg-type]


def test_naira_to_kobo_refuses_garbage() -> None:
    with pytest.raises(MoneyError, match="not a valid monetary amount"):
        naira_to_kobo("not-a-number")


def test_kobo_to_naira() -> None:
    assert kobo_to_naira(125_000) == Decimal("1250.00")
    with pytest.raises(MoneyError):
        kobo_to_naira("125000")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "₦0.00"),
        (1, "₦0.01"),
        (125_000, "₦1,250.00"),
        (3_312_000, "₦33,120.00"),
        (-50_000, "-₦500.00"),
        (100_000_000, "₦1,000,000.00"),
    ],
)
def test_format_money(amount: int, expected: str) -> None:
    assert format_money(amount) == expected


def test_format_money_unknown_currency_uses_code() -> None:
    assert format_money(125_000, "ZAR") == "ZAR 1,250.00"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "NGN 0.00"),
        (1, "NGN 0.01"),
        (3_312_000, "NGN 33,120.00"),
        (-50_000, "-NGN 500.00"),
    ],
)
def test_format_money_ascii(amount: int, expected: str) -> None:
    """The PDF-safe form. The naira sign is not in WinAnsiEncoding, and
    reportlab substitutes it silently — ``₦33,120.00`` prints as ``n33,120.00``
    on a receipt (see apps/orders/services/receipt.py)."""
    assert format_money_ascii(amount) == expected


def test_format_money_ascii_carries_no_symbol() -> None:
    assert "₦" not in format_money_ascii(125_000)
    assert format_money_ascii(125_000, "USD") == "USD 1,250.00"


def test_format_money_ascii_validates_its_inputs() -> None:
    with pytest.raises(MoneyError):
        format_money_ascii(100, "NAIRA")
    with pytest.raises(MoneyError):
        format_money_ascii(1.5)  # type: ignore[arg-type]


def test_format_money_validates_currency() -> None:
    with pytest.raises(MoneyError, match="ISO 4217"):
        format_money(100, "NAIRA")
    with pytest.raises(MoneyError):
        format_money(100, "N1G")


# ──────────────────────────────────────────────────────────────────────────────
# Money value object
# ──────────────────────────────────────────────────────────────────────────────


def test_money_construction_and_projection() -> None:
    money = Money(125_000)
    assert money.amount == 125_000
    assert money.currency == "NGN"
    assert money.display == "₦1,250.00"
    assert money.naira == Decimal("1250.00")
    assert str(money) == "₦1,250.00"


def test_money_wire_format() -> None:
    assert Money(3_312_000).as_dict() == {
        "amount": 3_312_000,
        "currency": "NGN",
        "display": "₦33,120.00",
    }


def test_money_constructors() -> None:
    assert Money.zero() == Money(0)
    assert Money.from_naira("14.90") == Money(1490)


def test_money_rejects_non_integer() -> None:
    with pytest.raises(MoneyError, match="integer number of kobo"):
        Money(14.90)  # type: ignore[arg-type]
    with pytest.raises(MoneyError):
        Money(True)  # type: ignore[arg-type]


def test_money_normalises_currency_case() -> None:
    assert Money(100, "ngn").currency == "NGN"


def test_money_arithmetic() -> None:
    assert Money(100) + Money(50) == Money(150)
    assert Money(100) - Money(50) == Money(50)
    assert Money(100) * 3 == Money(300)
    assert 3 * Money(100) == Money(300)
    assert -Money(100) == Money(-100)
    assert abs(Money(-100)) == Money(100)


def test_money_comparisons() -> None:
    assert Money(100) < Money(200)
    assert Money(100) <= Money(100)
    assert Money(200) > Money(100)
    assert Money(200) >= Money(200)
    assert bool(Money(1)) is True
    assert bool(Money(0)) is False


def test_money_refuses_cross_currency_operations() -> None:
    with pytest.raises(MoneyError, match="Cannot combine"):
        Money(100, "NGN") + Money(100, "USD")
    with pytest.raises(MoneyError):
        Money(100, "NGN") - Money(100, "USD")
    with pytest.raises(MoneyError):
        _ = Money(100, "NGN") < Money(100, "USD")


def test_money_returns_notimplemented_for_foreign_types() -> None:
    assert Money(100).__add__(5) is NotImplemented
    assert Money(100).__sub__(5) is NotImplemented
    assert Money(100).__mul__("3") is NotImplemented
    assert Money(100).__mul__(True) is NotImplemented


def test_money_is_immutable() -> None:
    money = Money(100)
    with pytest.raises((AttributeError, TypeError)):
        money.amount = 200  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# The structural guard
# ──────────────────────────────────────────────────────────────────────────────


def test_no_binary_floating_point_in_the_money_path() -> None:
    """The money module must never reference Python's binary float type.

    An AST check rather than a substring search: prose in a docstring that
    happens to mention the word must not fail the build, and a real usage
    hidden inside a string must not pass it.
    """
    source = pathlib.Path(__file__).resolve().parents[1] / "money.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "float" not in names, "float() used in the money path"
    assert "float" not in attributes, "a float attribute is referenced in the money path"

    literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert not literals, "a binary floating-point literal appears in the money path"
