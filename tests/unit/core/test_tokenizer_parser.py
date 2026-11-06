"""Tokenizer and strict v1 parser quirks (docs/05 §1, §3)."""

from __future__ import annotations

import pytest

from structura.core.lang.ast import CallAction
from structura.core.lang.diagnostics import ParseError
from structura.core.lang.legacy.parser import parse_legacy
from structura.core.lang.legacy.tokenizer import Kind, tokenize


def texts(source: str) -> list[str]:
    return [t.text for t in tokenize(source) if t.kind is not Kind.END]


def test_tabs_are_deleted_inside_tokens() -> None:
    assert texts("{ x\t1 } box") == ["{", "x1", "}", "box"]


def test_block_comment_starts_inside_line_comment() -> None:
    assert texts("q // b /* c\r\n d */ e") == ["q", "e"]


def test_hash_line_comment_and_brackets() -> None:
    assert texts("#define x\r\ntriangle[0,0,0; 1,0,0;0,1,0] box") == ["triangle[0,0,0; 1,0,0;0,1,0]", "box"]


def test_numbers_and_fractions() -> None:
    tokens = tokenize("3 -2 1/4 2.5e1")
    assert [(t.value, t.is_integer) for t in tokens[:4]] == [(3, True), (-2, True), (0.25, False), (25.0, False)]
    with pytest.raises(ParseError):
        tokenize("0/4")


def test_operator_abbreviations_resolve() -> None:
    assert texts("md w h b a c") == ["maxdepth", "weight", "hue", "brightness", "alpha", "color"]


def test_loop_and_modifiers() -> None:
    program = parse_legacy("2 * { x 1 } 3 * { y 1 } r\r\nrule r md 4 > q w 2 { box }\r\nrule q { }")
    action = program.top[0]
    assert isinstance(action, CallAction)
    assert [loop.count for loop in action.loops] == [2, 3]
    rule = program.rules[0]
    assert (rule.maxdepth, rule.retirement, rule.weight) == (4, "q", 2.0)


def test_size_and_v_aliases_are_accepted() -> None:
    ops = parse_legacy("{ size 2 v 0.5 } box").top[0].loops[0].ops  # type: ignore[union-attr]
    assert [op.name for op in ops] == ["s", "brightness"]


@pytest.mark.parametrize(
    "source",
    [
        "{ x } box",
        "rule { box }",
        "rule r { box",
        "box x 1",
        "{ color nope } box",
        "1.5 * { x 1 } box",
        "rule c { box }",
    ],
)
def test_rejected_like_structure_synth(source: str) -> None:
    with pytest.raises(ParseError):
        parse_legacy(source)
