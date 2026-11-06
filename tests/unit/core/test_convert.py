"""'structura convert --to v2' keeps what a v1 script builds (docs/16 §5)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.errors import StructuraError
from structura.core.lang.api import compile_script
from structura.core.lang.convert import convert_to_v2
from structura.core.lang.diagnostics import ParseError
from structura.core.lang.source import detect_dialect
from structura.core.scene.ir import PrimitiveKind as K
from structura.core.text_file import read_script

EXAMPLES = sorted((Path(__file__).parents[3] / "src/structura/resources/examples").rglob("*.es"))


def _same_build(a: str, b: str) -> None:
    one = build_scene(compile_script(a).program, 1).scene
    two = build_scene(compile_script(b).program, 1).scene
    drawn = two.kind != K.CYLINDER  # v1 cylinders draw nothing; v2 ones do
    assert np.array_equal(one.kind, two.kind[drawn]) and np.array_equal(one.xform, two.xform[drawn])
    assert np.array_equal(one.rgba, two.rgba[drawn])


def test_substring_defines_are_written_out() -> None:
    text = "#define R 3\nR * { x 1 } R1\nrule R1 { box }\n"
    converted = convert_to_v2(text)
    assert detect_dialect(converted.text) == 2 and "31" in converted.text and "#define R 3" in converted.text
    assert any("whole words" in n for n in converted.notes)
    with pytest.raises(ParseError):
        compile_script(text)  # in 1.5 this script does not even parse ('R1' → '31')…
    with pytest.raises(ParseError):
        compile_script(converted.text)  # … and the converted script fails the same way


def test_rules_named_like_v2_keywords_are_renamed() -> None:
    text = "Tube\nrule tube { { x 1 } box::tube mat }\nrule mat { sphere }\n"
    converted = convert_to_v2(text)
    assert "rule tube_rule" in converted.text and "Tube_rule" not in converted.text.split("\n")[1]
    assert "box::tube" in converted.text and "rule mat_rule" in converted.text
    _same_build(text, converted.text)


def test_cylinders_are_reported() -> None:
    notes = convert_to_v2("cylinder\nbox\n").notes
    assert any("cylinder" in n and "line 1" in n for n in notes)


def test_v2_scripts_are_left_alone() -> None:
    text = "#version 2\nbox\n"
    assert convert_to_v2(text).text == text and not convert_to_v2(text).changed


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_every_bundled_example_builds_the_same_after_conversion(path: Path) -> None:
    text = read_script(path)
    if detect_dialect(text) == 2 or text.lstrip().startswith("#javascript"):
        pytest.skip("not a v1 EisenScript")
    try:
        compile_script(text)
    except StructuraError:
        pytest.skip("does not build in 1.5 either")
    _same_build(text, convert_to_v2(text).text)
