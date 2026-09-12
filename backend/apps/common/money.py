"""Money primitives.

The single rule this module exists to enforce: **money is an integer count of
kobo**. ₦1,250.00 is ``125000``. Binary floating-point arithmetic is never used
anywhere in a money path, because ``0.1 + 0.2 != 0.3`` and money that drifts is
money that gets argued about.

Where a ratio is unavoidable (percentage discounts, VAT extraction) the
intermediate is a :class:`decimal.Decimal` and the result is rounded to whole
kobo immediately with ``ROUND_HALF_UP``.

See ``docs/ARCHITECTURE.md`` §4 and ``docs/PAYMENTS.md`` §7.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

KOBO_PER_NAIRA = 100
"""Minor units per major unit. NGN has 2 decimal places."""

BPS_DIVISOR = 10_000
"""Basis points are hundredths of a percent: 750 bps == 7.5%."""

DEFAULT_CURRENCY = "NGN"
DEFAULT_VAT_RATE_BPS = 750

CURRENCY_SYMBOLS = {"NGN": "₦", "USD": "$", "GBP": "£", "EUR": "€"}

#: Types accepted when converting a major-unit value to kobo. Inexact binary
#: fractions are rejected on purpose — see :func:`naira_to_kobo`.
ExactNumber = int | str | Decimal


class MoneyError(ValueError):
    """Raised when a money value or operation is invalid."""


# ──────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────────────


def _ensure_int(value: object, name: str) -> int:
    """Reject anything that is not a true integer.

    ``bool`` is a subclass of ``int`` in Python, so it is excluded explicitly:
    ``Money(True)`` is a bug, not one kobo.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise MoneyError(
            f"{name} must be an integer number of kobo, got {type(value).__name__!r}. "
            "Binary floating-point values are not permitted in a money path; "
            "use naira_to_kobo() with a str or Decimal."
        )
    return value


def _ensure_non_negative(value: int, name: str) -> int:
    _ensure_int(value, name)
    if value < 0:
        raise MoneyError(f"{name} must not be negative, got {value}.")
    return value


def _ensure_rate_bps(rate_bps: int) -> int:
    _ensure_non_negative(rate_bps, "rate_bps")
    if rate_bps > BPS_DIVISOR:
        raise MoneyError(f"rate_bps must not exceed {BPS_DIVISOR} (100%), got {rate_bps}.")
    return rate_bps


def _ensure_currency(currency: str) -> str:
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        raise MoneyError(f"currency must be a 3-letter ISO 4217 code, got {currency!r}.")
    return currency.upper()


# ──────────────────────────────────────────────────────────────────────────────
# Rounding and conversion
# ──────────────────────────────────────────────────────────────────────────────


def round_half_up(value: Decimal) -> int:
    """Round a :class:`Decimal` to a whole number of kobo, ties away from zero.

    This is the only rounding function in the codebase. Applying it once per
    component (never accumulating it across line items) is what keeps totals
    reconcilable to the kobo.
    """
    if not isinstance(value, Decimal):
        raise MoneyError(f"round_half_up expects a Decimal, got {type(value).__name__!r}.")
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def naira_to_kobo(value: ExactNumber) -> int:
    """Convert a major-unit amount to kobo.

    Accepts ``int``, ``str`` or ``Decimal`` only. A binary floating-point value
    such as ``14.90`` is rejected because it is not exactly representable, which
    is precisely the defect this module exists to prevent.

    >>> naira_to_kobo("14.90")
    1490
    """
    if isinstance(value, bool) or not isinstance(value, int | str | Decimal):
        raise MoneyError(
            f"naira_to_kobo expects int, str or Decimal, got {type(value).__name__!r}. "
            "Binary floating-point values are not exactly representable and are refused."
        )
    try:
        as_decimal = Decimal(str(value))
    except ArithmeticError as exc:
        raise MoneyError(f"{value!r} is not a valid monetary amount.") from exc
    return round_half_up(as_decimal * KOBO_PER_NAIRA)


def kobo_to_naira(amount_kobo: int) -> Decimal:
    """Convert kobo to a major-unit :class:`Decimal`. For display and reporting only."""
    _ensure_int(amount_kobo, "amount_kobo")
    return (Decimal(amount_kobo) / KOBO_PER_NAIRA).quantize(Decimal("0.01"))


def format_money(amount_kobo: int, currency: str = DEFAULT_CURRENCY) -> str:
    """Render kobo as a display string, e.g. ``₦12,500.00``.

    Pure integer arithmetic — no locale machinery, no rounding surprises. The API
    ships this string so that clients never format currency themselves.
    """
    _ensure_int(amount_kobo, "amount_kobo")
    currency = _ensure_currency(currency)
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    sign = "-" if amount_kobo < 0 else ""
    whole, fraction = divmod(abs(amount_kobo), KOBO_PER_NAIRA)
    return f"{sign}{symbol}{whole:,}.{fraction:02d}"


def format_money_ascii(amount_kobo: int, currency: str = DEFAULT_CURRENCY) -> str:
    """Render kobo with the ISO code rather than the symbol: ``NGN 12,500.00``.

    For PDFs, and anywhere else the naira sign cannot be trusted to survive.
    The standard PDF fonts use WinAnsiEncoding, which has no U+20A6: reportlab
    substitutes it silently, so ``₦3,312.00`` prints on a receipt as
    ``n3,312.00``. An ISO code is unambiguous and always renders.
    """
    _ensure_int(amount_kobo, "amount_kobo")
    currency = _ensure_currency(currency)
    sign = "-" if amount_kobo < 0 else ""
    whole, fraction = divmod(abs(amount_kobo), KOBO_PER_NAIRA)
    return f"{sign}{currency} {whole:,}.{fraction:02d}"


# ──────────────────────────────────────────────────────────────────────────────
# Tax
# ──────────────────────────────────────────────────────────────────────────────


def extract_vat(gross_kobo: int, rate_bps: int = DEFAULT_VAT_RATE_BPS) -> int:
    """Return the VAT *already contained* in a VAT-inclusive amount.

    Used when ``Branch.prices_include_vat`` is ``True`` (the default): the menu
    price is what the customer pays, and VAT is extracted from it for accounting.

    ``vat = gross × rate / (10000 + rate)``

    >>> extract_vat(3_312_000, 750)
    231070
    """
    _ensure_non_negative(gross_kobo, "gross_kobo")
    _ensure_rate_bps(rate_bps)
    if rate_bps == 0:
        return 0
    return round_half_up(Decimal(gross_kobo) * rate_bps / (BPS_DIVISOR + rate_bps))


def add_vat(net_kobo: int, rate_bps: int = DEFAULT_VAT_RATE_BPS) -> int:
    """Return the VAT to add *on top of* a VAT-exclusive amount.

    Used when ``Branch.prices_include_vat`` is ``False``.

    ``vat = net × rate / 10000``
    """
    _ensure_non_negative(net_kobo, "net_kobo")
    _ensure_rate_bps(rate_bps)
    return round_half_up(Decimal(net_kobo) * rate_bps / BPS_DIVISOR)


def vat_for(amount_kobo: int, rate_bps: int, *, inclusive: bool) -> int:
    """Dispatch to :func:`extract_vat` or :func:`add_vat` by branch policy."""
    return extract_vat(amount_kobo, rate_bps) if inclusive else add_vat(amount_kobo, rate_bps)


# ──────────────────────────────────────────────────────────────────────────────
# Proportions
# ──────────────────────────────────────────────────────────────────────────────


def apply_bps(amount_kobo: int, bps: int, *, cap: int | None = None) -> int:
    """Apply a basis-point proportion, optionally capped.

    Used for percentage promo codes: ``apply_bps(subtotal, 1000, cap=500_000)``
    is "10% off, up to ₦5,000".
    """
    _ensure_non_negative(amount_kobo, "amount_kobo")
    _ensure_non_negative(bps, "bps")
    result = round_half_up(Decimal(amount_kobo) * bps / BPS_DIVISOR)
    if cap is not None:
        _ensure_non_negative(cap, "cap")
        result = min(result, cap)
    return result


def allocate(amount_kobo: int, weights: Sequence[int]) -> list[int]:
    """Split an amount across weights so the parts sum **exactly** to the whole.

    Largest-remainder method: every part is floored, then the leftover kobo are
    handed out one at a time to the largest remainders. Without this, a discount
    spread across three lines loses or invents a kobo and the order stops
    reconciling.

    >>> allocate(1000, [1, 1, 1])
    [334, 333, 333]
    """
    _ensure_int(amount_kobo, "amount_kobo")
    if not weights:
        raise MoneyError("allocate requires at least one weight.")
    for weight in weights:
        _ensure_non_negative(weight, "weight")

    total_weight = sum(weights)
    if total_weight == 0:
        # Nothing to weight by: give everything to the first bucket.
        return [amount_kobo] + [0] * (len(weights) - 1)

    floors: list[int] = []
    remainders: list[tuple[Decimal, int]] = []
    for index, weight in enumerate(weights):
        exact = Decimal(amount_kobo) * weight / total_weight
        floor = int(exact.to_integral_value(rounding="ROUND_FLOOR"))
        floors.append(floor)
        remainders.append((exact - floor, index))

    leftover = amount_kobo - sum(floors)
    # Ties break on the earlier index so the result is deterministic.
    remainders.sort(key=lambda pair: (-pair[0], pair[1]))
    for offset in range(abs(leftover)):
        _, index = remainders[offset % len(remainders)]
        floors[index] += 1 if leftover > 0 else -1
    return floors


def compute_total(amounts: Iterable[int]) -> int:
    """Sum integer kobo amounts.

    Trivial by design: three lines of ₦3.33 total ₦9.99, never ₦10.00, because
    nothing was ever rounded on the way in.
    """
    total = 0
    for amount in amounts:
        total += _ensure_int(amount, "amount")
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Value object
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable amount of money in minor units.

    >>> Money(125000).display
    '₦1,250.00'
    """

    amount: int
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        _ensure_int(self.amount, "amount")
        object.__setattr__(self, "currency", _ensure_currency(self.currency))

    # ── constructors ──────────────────────────────────────────────────────────

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> Money:
        return cls(0, currency)

    @classmethod
    def from_naira(cls, value: ExactNumber, currency: str = DEFAULT_CURRENCY) -> Money:
        return cls(naira_to_kobo(value), currency)

    # ── projections ───────────────────────────────────────────────────────────

    @property
    def naira(self) -> Decimal:
        return kobo_to_naira(self.amount)

    @property
    def display(self) -> str:
        return format_money(self.amount, self.currency)

    def as_dict(self) -> dict[str, object]:
        """The wire format every money value takes in the API."""
        return {"amount": self.amount, "currency": self.currency, "display": self.display}

    # ── arithmetic ────────────────────────────────────────────────────────────

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise MoneyError(f"Cannot combine {self.currency} with {other.currency}.")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int) -> Money:
        """Multiply by a whole quantity. Ratios go through :func:`apply_bps`."""
        if isinstance(factor, bool) or not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount * factor, self.currency)

    __rmul__ = __mul__

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __lt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount >= other.amount

    def __bool__(self) -> bool:
        return self.amount != 0

    def __str__(self) -> str:
        return self.display
