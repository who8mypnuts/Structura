"""File-size estimates for the export sheet (docs/14 §5.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.export.api import export_scene
from structura.export.estimate import estimate_size, human

SCENE = build_scene(compile_script("30 * { x 1 } 30 * { y 1 } box\n").program).scene  # 900 boxes


@pytest.mark.parametrize(("name", "suffix"), [("stl", ".stl"), ("ply", ".ply"), ("gltf", ".glb"), ("obj", ".obj")])
def test_estimates_are_within_ten_percent(tmp_path: Path, name: str, suffix: str) -> None:
    report = export_scene(SCENE, tmp_path / f"x{suffix}", name, {})
    real = sum(p.stat().st_size for p in {*report.files, tmp_path / f"x{suffix}"} if p.exists())
    assert abs(estimate_size(SCENE, name, suffix, {}) / real - 1) < 0.1


def test_human_sizes() -> None:
    assert human(512) == "512 bytes" and human(2048) == "2.0 KB" and human(5 * 2**20) == "5.0 MB"
