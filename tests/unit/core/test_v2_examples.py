"""The bundled EisenScript v2 examples (the gallery's 'Structura v2' group) are clean and build (PLAN Phase 10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script

FOLDER = Path(__file__).resolve().parents[3] / "src/structura/resources/examples/v2"
EXAMPLES = sorted(FOLDER.glob("*.es"))


def test_there_are_v2_examples() -> None:
    assert len(EXAMPLES) >= 6


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_is_clean_v2_and_builds(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#version 2\n")
    assert [(d.code, d.message) for d in analyze(text).diagnostics] == []
    scene = build_scene(compile_script(text, script_dir=path.parent).program).scene
    assert len(scene) > 0 and scene.declarations is not None
