"""Model fields shared across apps."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.core.validators import RegexValidator
from django.db import models

KOBO_HELP = "Amount in kobo (₦1.00 = 100). Never enter naira here."

phone_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{7,14}$",
    message="Enter a phone number in international format, e.g. +2348012345678.",
)


class MoneyField(models.PositiveBigIntegerField):
    """A non-negative amount of money in minor units (kobo).

    Exists so that no one ever has to wonder whether a column is naira or kobo:
    the help text says kobo, and the type cannot hold a fractional value.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("help_text", KOBO_HELP)
        # A nullable money field must default to NULL, not 0. They mean different
        # things: a free-delivery threshold of NULL is "no threshold", while 0
        # would mean "free delivery on every order".
        if not kwargs.get("null"):
            kwargs.setdefault("default", 0)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("help_text") == KOBO_HELP:
            del kwargs["help_text"]
        if kwargs.get("default") == 0:
            del kwargs["default"]
        return name, path, args, kwargs


class SignedMoneyField(models.BigIntegerField):
    """A money amount that may legitimately be negative.

    Used for price deltas (a smaller portion may cost less) and ledger entries.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("help_text", KOBO_HELP + " May be negative.")
        kwargs.setdefault("default", 0)
        super().__init__(*args, **kwargs)


class PhoneField(models.CharField):
    """E.164-ish phone number."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("validators", [phone_validator])
        super().__init__(*args, **kwargs)
