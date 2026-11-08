"""Refactorings (docs/12 §2.2): extract a rule, inline a rule, '{…} R' ↔ '1 * {…} R'. Each keeps the
structure the script builds."""

from __future__ import annotations

import numpy as np

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.lang.fixes import apply_edits
from structura.core.lang.restructure import refactorings_at, rule_alone

SCRIPT = """{ x 1 } R
3 * { ry 5 } 2 * { s 0.9 } R
rule R { box { x 1 } sphere 1 * { y 2 } dot }
"""


def _build(text: str) -> np.ndarray:
    program = compile_script(text).program
    assert program is not None, text
    scene = build_scene(program, 1).scene
    return np.sort(np.round(scene.base, 4).view(np.dtype((np.void, 12))).ravel())


def _apply(text: str, position: int, title: str) -> str:
    fix = next(f for f in refactorings_at(text, position) if f.title.startswith(title))
    return apply_edits(text, fix.edits)


def test_each_refactoring_keeps_the_structure() -> None:
    before = _build(SCRIPT)
    at_call, at_rule = SCRIPT.index("ry"), SCRIPT.index("rule R") + 2
    for position, title in ((at_call, "Extract"), (at_call, "Inline 'R' here"), (3, "Inline 'R' here"),
                            (at_rule, "Inline rule 'R' everywhere"), (3, "Convert to '1 *")):  # fmt: skip
        after = _apply(SCRIPT, position, title)
        assert np.array_equal(_build(after), before), (title, after)


def test_extract_names_the_rule_and_inline_everywhere_removes_it() -> None:
    extracted = _apply(SCRIPT, SCRIPT.index("ry"), "Extract")
    assert "\nnewRule\n" in extracted and "rule newRule {\n  3 * { ry 5 } 2 * { s 0.9 } R\n}" in extracted
    inlined = _apply(SCRIPT, SCRIPT.index("rule R") + 2, "Inline rule")
    assert "rule" not in inlined and inlined.count("box") == 2


def test_the_count_toggle_goes_both_ways_and_only_where_valid() -> None:
    assert _apply("{ x 1 } box\n", 2, "Convert") == "1 * { x 1 } box\n"
    assert _apply("1 * { x 1 } box\n", 2, "Convert") == "{ x 1 } box\n"
    titles = [f.title for f in refactorings_at("2 * { x 1 } box\n", 2)]
    assert not any(t.startswith("Convert") for t in titles)


def test_recursive_weighted_and_substituted_rules_are_left_alone() -> None:
    recursive = "R\nrule R maxdepth 3 { { x 1 } R box }\n"
    assert not any(f.title.startswith("Inline") for f in refactorings_at(recursive, 0))
    ambiguous = "R\nrule R { box }\nrule R { sphere }\n"
    assert not any(f.title.startswith("Inline") for f in refactorings_at(ambiguous, 0))
    defined = "#define N 3\nN * { x 1 } box\n"
    assert refactorings_at(defined, defined.index("{")) == []  # the line has a substitution


def test_a_rule_alone_keeps_settings_and_definitions() -> None:
    text = "set maxdepth 20\n{ x 3 } R\nbox\nrule R { sphere { y 1 } T }\nrule T { box }\n"
    alone = rule_alone(text, "T")
    assert alone is not None and alone.startswith("set maxdepth 20\n") and alone.endswith("\nT\n")
    assert "{ x 3 } R" not in alone and len(_build(alone)) == 1
    assert rule_alone(text, "missing") is None


def test_the_object_estimate_follows_loops_weights_and_depths() -> None:
    from structura.core.lang.analysis import analyze  # noqa: PLC0415

    def estimate(text: str) -> list[str]:
        return [h.text for h in analyze(text).hints if h.kind == "estimate"]

    assert estimate("R\nrule R maxdepth 5 { { x 1 } R box }\n") == ["≈ 5 objects"]
    assert estimate("R\nrule R maxdepth 3 { { x 1 } R { y 1 } R box }\n") == ["≈ 7 objects"]
    assert estimate("R\nrule R { { x 1 } R { y 1 } R box }\n") == ["≈ 65.5k objects (limit)"]  # as the builder: 65535
    assert estimate("3 * { x 1 } T\nrule T { 2 * { y 1 } box }\n") == ["≈ 6 objects"]
    assert estimate("box\n") == []  # only calls of rules get an estimate


def test_the_estimate_equals_the_builder_for_deterministic_scripts() -> None:
    from structura.core.lang.ast import CallAction  # noqa: PLC0415
    from structura.core.lang.estimate import Estimator  # noqa: PLC0415
    from structura.core.lang.legacy.parser import parse_legacy  # noqa: PLC0415

    for text in ("set maxdepth 8\nR\nrule R { { x 1 } R { y 1 } R box }\n",
                 "set maxobjects 1000\nR\nrule R { { x 1 } R { y 1 } R box }\n",
                 "R\nrule R maxdepth 3 { { x 1 } R { y 1 } R box }\n",
                 "3 * { x 1 } T\nrule T { 2 * { y 1 } box }\n"):  # fmt: skip
        program = parse_legacy(text)
        call = next(a for a in program.top if isinstance(a, CallAction))
        assert Estimator(program).call(call)[0] == len(_build(text)), text
