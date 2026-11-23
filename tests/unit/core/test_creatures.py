"""Medusarium: the bundled creature examples are clean, build, and expose their anatomy as GUI parameters (PLAN M1)."""

from __future__ import annotations

import dataclasses
import io
from pathlib import Path

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR

FOLDER = Path(__file__).resolve().parents[3] / "src/structura/resources/examples/creatures"
EXAMPLES = sorted(FOLDER.glob("*.es"))


def test_there_are_creature_examples() -> None:
    assert len(EXAMPLES) >= 1


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_creature_is_clean_v2_and_builds(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#version 2\n")
    assert [(d.code, d.message) for d in analyze(text).diagnostics] == []
    scene = build_scene(compile_script(text, script_dir=path.parent).program).scene
    assert len(scene) > 0 and scene.declarations is not None


def _digest(scene: SceneIR) -> bytes:
    """The SceneIR's numpy payloads as bytes, so two builds can be compared for equality."""
    arrays = {
        f.name: getattr(scene, f.name)
        for f in dataclasses.fields(scene)
        if isinstance(getattr(scene, f.name), np.ndarray)
    }
    buf = io.BytesIO()
    np.savez(buf, **arrays)
    return buf.getvalue()


def test_medusa_exposes_its_anatomy_as_parameters() -> None:
    analysis = analyze((FOLDER / "medusa.es").read_text(encoding="utf-8"))
    by_name = {p.name: p for p in analysis.parameters}
    assert set(by_name) >= {
        "radius", "tentacles", "segments", "bend", "taper",
        "oral", "lobes", "fringe", "fringe_depth", "bell_color", "tent_color",
    }
    assert by_name["tentacles"].kind == "int"
    assert by_name["bend"].kind == "float"
    assert by_name["bell_color"].kind == "color"
    assert by_name["tentacles"].minimum <= 10 and by_name["tentacles"].maximum >= 32


def test_medusa_param_extremes_build() -> None:
    text = (FOLDER / "medusa.es").read_text(encoding="utf-8")
    extremes = [
        {"tentacles": 1, "oral": 1, "lobes": 0, "fringe": 0},  # zero-division guards
        {"tentacles": 32, "segments": 30, "fringe": 160, "fringe_depth": 16, "lobes": 24},  # panel maxima
    ]
    for params in extremes:
        scene = build_scene(compile_script(text, script_dir=FOLDER, params=params).program).scene
        assert len(scene) > 0


def test_medusa_seed_changes_geometry() -> None:
    text = (FOLDER / "medusa.es").read_text(encoding="utf-8")
    a = _digest(build_scene(compile_script(text, script_dir=FOLDER).program, seed=7).scene)
    b = _digest(build_scene(compile_script(text, script_dir=FOLDER).program, seed=99).scene)
    assert a != b
