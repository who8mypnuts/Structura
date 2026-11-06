"""Rename, references and formatting work on tokens: comments, tags and strings are untouched (docs/12)."""

from __future__ import annotations

import pytest

from structura.core.lang.refactor import format_script, rename_rule, rule_occurrences

TEXT = "R1 // R1 here\nrule R1 md 3 > R1 {\n{ x 1 } R1\n     box::R1\n}\n/* R1 */\n"


def test_rename_touches_definitions_and_references_only() -> None:
    out = rename_rule(TEXT, "r1", "Spiral")
    assert out.count("Spiral") == 4 and "// R1 here" in out and "box::R1" in out and "/* R1 */" in out
    assert len(rule_occurrences(TEXT, "R1")) == 4
    with pytest.raises(ValueError):
        rename_rule(TEXT, "r1", "two words")


def test_format_reindents_by_brace_depth_and_is_idempotent() -> None:
    messy = "rule A {\n{ x 1 } A\n    rule B {\nbox } }\n  sphere   \n/* keep\n   this */\n"
    tidy = format_script(messy)
    assert tidy.splitlines()[:5] == ["rule A {", "  { x 1 } A", "  rule B {", "    box } }", "sphere"]
    assert format_script(tidy) == tidy and "   this */" in tidy
