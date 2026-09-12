"""The compliance guard.

PCI-DSS SAQ A depends on one property: raw cardholder data never reaches our
infrastructure. These tests assert that structurally rather than by convention.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

PAYMENTS = pathlib.Path(__file__).resolve().parents[1]

#: Names that would indicate we are handling raw cardholder data.
FORBIDDEN = {
    "card_number",
    "cardnumber",
    "pan",
    "cvv",
    "cvc",
    "card_cvv",
    "security_code",
    "card_expiry",
}

#: What a provider legitimately hands back for display.
ALLOWED = {"card_last4", "card_brand", "card_exp_month", "card_exp_year"}


def python_files() -> list[pathlib.Path]:
    return [
        path
        for path in PAYMENTS.rglob("*.py")
        if "migrations" not in path.parts and path.name != "test_no_card_data.py"
    ]


def test_no_model_field_can_hold_cardholder_data() -> None:
    """A field for a PAN or CVV must not exist. Not blank, not optional — absent."""
    from apps.payments.models import PaymentTransaction, Refund, WebhookEvent

    for model in (PaymentTransaction, Refund, WebhookEvent):
        names = {field.name.lower() for field in model._meta.fields}
        offending = names & FORBIDDEN
        assert not offending, f"{model.__name__} has cardholder fields: {offending}"


def test_no_serializer_accepts_card_details() -> None:
    """If no serializer field exists, no request body can carry one in."""
    from apps.payments.serializers import InitialiseSerializer, RefundSerializer

    for serializer_class in (InitialiseSerializer, RefundSerializer):
        names = {name.lower() for name in serializer_class().fields}
        assert not names & FORBIDDEN, f"{serializer_class.__name__} accepts card data"


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_source_file_references_cardholder_data(path: pathlib.Path) -> None:
    """AST-level check across the whole payments package.

    Catches an identifier that a grep over prose would miss, and ignores the
    word appearing in a docstring, which a grep would falsely flag.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr.lower())
        elif isinstance(node, ast.arg):
            identifiers.add(node.arg.lower())
        elif isinstance(node, ast.keyword) and node.arg:
            identifiers.add(node.arg.lower())

    offending = (identifiers & FORBIDDEN) - ALLOWED
    assert not offending, f"{path.name} references cardholder data: {offending}"
