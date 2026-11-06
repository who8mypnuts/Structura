"""Legacy preprocessor semantics (docs/05 §2), each confirmed against Structure Synth 1.5."""

from __future__ import annotations

from structura.core.lang.legacy.gui_params import apply_gui_parameters, default_value
from structura.core.lang.legacy.preprocessor import LegacyPreprocessor


def _run(text: str, seed: int = 0) -> str:
    return LegacyPreprocessor().process(text, seed).text


def test_define_is_raw_substring_replacement() -> None:
    out = _run("#define s 2\nrule r { { s s } box }").split("\r\n")
    assert out[1] == "rule r { { 2 2 } box }"


def test_recursive_define_is_applied_until_cap() -> None:
    result = LegacyPreprocessor().process("#define rec rec2\n{ x 1 } rec")
    assert "rec2222" in result.text
    assert any(d.code == "W104" for d in result.diagnostics)


def test_identical_random_texts_share_one_draw() -> None:
    line = _run("{ x random[0,1] y random[0,1] } box", seed=3)
    values = [tok for tok in line.split() if tok[0].isdigit()]
    assert values[0] == values[1] == "0.550798"  # value observed from Structure Synth 1.5 (seed 3)


def test_gui_parameters_round_to_two_decimals_and_clamp() -> None:
    result = LegacyPreprocessor().process("#define a 0.3333 (float:0-1)\n#define n 120 (int:1-90)\nx")
    a, n = result.parameters
    assert (default_value(a), default_value(n)) == (0.33, 90.0)
    assert apply_gui_parameters("a n", result.parameters) == "0.33 90"


def test_line_structure_is_preserved() -> None:
    assert _run("a\r\nb\nc\rd").split("\r\n") == ["a", "b", "c", "d"]
