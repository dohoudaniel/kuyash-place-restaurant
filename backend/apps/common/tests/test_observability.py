"""Sentry scrubbing tests.

This is a security control, not a nicety: it is the last thing standing between
a credential and a third-party service. See docs/SECURITY.md §6.
"""

from __future__ import annotations

import pytest

from apps.common.observability import REDACTED, scrub_event


def test_sensitive_top_level_keys_are_redacted() -> None:
    event = scrub_event({"password": "hunter2", "email": "ada@example.com"}, None)
    assert event["password"] == REDACTED
    assert event["email"] == "ada@example.com"  # not a secret, keep it useful


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "password1",
        "token",
        "guest_token",
        "secret",
        "authorization",
        "csrftoken",
        "sessionid",
        "cvv",
        "card_number",
        "pan",
        "authorization_code",
        "api_key",
        "secret_key",
    ],
)
def test_every_sensitive_key_is_covered(key: str) -> None:
    assert scrub_event({key: "sensitive"}, None)[key] == REDACTED


def test_key_matching_is_case_insensitive() -> None:
    assert scrub_event({"PASSWORD": "hunter2"}, None)["PASSWORD"] == REDACTED


def test_nested_structures_are_scrubbed() -> None:
    event = scrub_event(
        {"request": {"data": {"password": "hunter2", "items": [{"cvv": "123"}]}}}, None
    )
    assert event["request"]["data"]["password"] == REDACTED
    assert event["request"]["data"]["items"][0]["cvv"] == REDACTED


def test_non_dict_values_pass_through() -> None:
    event = scrub_event({"count": 3, "tags": ["a", "b"], "ok": True}, None)
    assert event == {"count": 3, "tags": ["a", "b"], "ok": True}


def test_deep_recursion_is_bounded() -> None:
    """A pathological payload must not blow the stack on the way to Sentry."""
    payload: dict = {"level": 0}
    node = payload
    for depth in range(1, 40):
        node["child"] = {"level": depth}
        node = node["child"]
    assert scrub_event(payload, None)["level"] == 0
