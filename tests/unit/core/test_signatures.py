"""Signature help for v2 expression functions (docs/12 §3)."""

from __future__ import annotations

from structura.core.lang.signatures import SIGNATURES, signature_at
from structura.core.lang.v2.expressions import FUNCTIONS


def test_every_expression_function_has_a_signature() -> None:
    assert set(SIGNATURES) == set(FUNCTIONS)


def test_active_argument_follows_top_level_commas() -> None:
    text = "{ x (clamp(sin(30), 0"
    sig = signature_at(text, len(text))
    assert sig is not None and sig.name == "clamp" and sig.active == 1
    assert sig.label == "clamp(x, lo, hi)"
    inner = signature_at(text, text.index("30") + 1)
    assert inner is not None and inner.name == "sin" and inner.active == 0


def test_no_signature_outside_calls_or_for_unknown_names() -> None:
    assert signature_at("{ x (sin(30)) } box", 14) is None
    assert signature_at("{ x (foo(1", 10) is None
    assert signature_at("rule r {\n x 1", 13) is None


def test_operator_arguments_inside_transform_lists() -> None:
    def at(text: str) -> tuple[str, int] | None:
        sig = signature_at(text, len(text))
        return (sig.label, sig.active) if sig else None

    assert at("{ s ") == ("s ‹float› [‹float› ‹float›]", 0)
    assert at("{ s 1 ") == ("s ‹float› [‹float› ‹float›]", 1)  # optional y z may follow
    assert at("{ s 1 x ") == ("x ‹float›", 0)  # 's 1' is complete, so 'x' starts a new operator
    assert at("{ blend red ") == ("blend ‹color› ‹float›", 1)
    assert at("{ rx 10 ") is None and at("{ x 1 } r ") is None
    assert at("{ x (sin(3") == ("sin(degrees)", 0)  # an expression function wins inside parentheses
