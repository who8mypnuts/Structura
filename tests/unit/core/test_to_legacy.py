"""Save as Legacy .es (docs/14 §4.1): v2 flattened to what Structure Synth 1.5 parses, v1 aliases respelled."""

from __future__ import annotations

from structura.core.lang.legacy.parser import parse_legacy
from structura.core.lang.legacy.preprocessor import LegacyPreprocessor
from structura.core.lang.to_legacy import legacy_copy

V2 = """#version 2
#param k float = 2 range 1..4
#define N 3
material gold { base #fc6 metallic 1 }
N * { x (k * 1.5) mat gold size 2 } R
rule R { box 2 * { y 1 } cone { y 1 } torus[0.2] sphere }
"""


def test_v2_is_flattened_for_1_5() -> None:
    copy = legacy_copy(V2)
    assert "#version" not in copy.text and "#define k 2 (float:1-4)" in copy.text
    assert "x 3 " in copy.text and "mat" not in copy.text and "cone" not in copy.text and "torus" not in copy.text
    assert "{ x 3  s 2 } R" in copy.text
    parse_legacy(LegacyPreprocessor(False).process(copy.text, 0).text)  # 1.5's grammar accepts it
    assert len(copy.notes) == 5


def test_v1_only_loses_the_aliases() -> None:
    text = "3 * { size 2 v 0.5 } box // size v stay in comments\n"
    copy = legacy_copy(text)
    assert copy.text == "3 * { s 2 brightness 0.5 } box // size v stay in comments\n"
    assert legacy_copy("box\n") == type(copy)("box\n", ())
