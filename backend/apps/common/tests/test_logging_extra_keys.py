"""No log call may pass a reserved LogRecord attribute through `extra`.

`logger.info("...", extra={"message": ...})` raises KeyError — but only when that
level is enabled. Tests run with quieter logging than development, so the crash
hides from the suite and surfaces as a 500 in front of a real request. This is a
static check, so it does not depend on log levels at all.
"""

from __future__ import annotations

import ast
import logging
import pathlib

APPS = pathlib.Path(__file__).resolve().parents[2]
RESERVED = set(vars(logging.LogRecord("x", 0, "x", 0, "x", None, None))) | {"message", "asctime"}


def test_no_log_call_passes_a_reserved_extra_key() -> None:
    offenders = []
    for path in APPS.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg == "extra" and isinstance(keyword.value, ast.Dict):
                    offenders.extend(
                        f"{path.relative_to(APPS.parent)}:{node.lineno} uses {key.value!r}"
                        for key in keyword.value.keys
                        if isinstance(key, ast.Constant) and key.value in RESERVED
                    )
    assert offenders == [], "Reserved LogRecord keys in extra=: " + "; ".join(offenders)
