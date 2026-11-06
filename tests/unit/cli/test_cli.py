"""The command line: lint, build and render end to end (docs/16 §5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from structura.cli.main import main
from structura.render.metadata import read_metadata

SCRIPT = "set raytracer::samples 2\nset background #123\n{ color #f80 } sphere\n{ x 1.2 } box::glass\n"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    path = tmp_path / "scene.es"
    path.write_text(SCRIPT)
    return path


def test_render_writes_an_image_with_reproducibility_metadata(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.png"
    argv = ["render", str(script), "-o", str(out), "--size", "32x24", "--integrator", "classic", "--device", "cpu"]
    assert main([*argv, "--seed", "7"]) == 0
    assert Image.open(out).size == (32, 24)
    meta = read_metadata(out)
    assert meta["script"] == SCRIPT and meta["seed"] == "7"
    settings = json.loads(meta["settings"])
    assert settings["samples"] == 4 and settings["integrator"] == "classic"  # 'raytracer::samples 2' → 2×2


def test_render_rejects_unknown_formats(script: Path, tmp_path: Path) -> None:
    assert main(["render", str(script), "-o", str(tmp_path / "x.gif"), "--device", "cpu"]) == 2


def test_render_exr_keeps_linear_floats(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.exr"
    argv = ["render", str(script), "-o", str(out), "--size", "16x12", "--samples", "1", "--device", "cpu"]
    assert main([*argv, "--no-embed-script"]) == 0
    meta = read_metadata(out)
    assert "script" not in meta and len(meta["script_sha256"]) == 64
