"""The Python API and the animation command (docs/16)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

import structura.api as st
from structura.cli.main import main

ANIMATED = "#version 2\nrender { integrator preview size 32x24 }\n{ rz (time * 90) } box\n"


def test_build_render_export_round_trip(tmp_path: Path) -> None:
    scene = st.build(ANIMATED, frame=12, fps=24)
    assert np.isclose(scene.xform[0, 0, 0], np.cos(np.radians(45)), atol=1e-6)  # time = 0.5 s → 45°
    result = st.render(scene, tmp_path / "a.png", device="cpu", samples=1)
    assert result.samples == 1 and Image.open(tmp_path / "a.png").size == (32, 24)
    assert st.export(scene, tmp_path / "a.glb").counts["triangles"] == 12


def test_animate_writes_numbered_frames_and_a_gif(tmp_path: Path) -> None:
    script = tmp_path / "anim.es"
    script.write_text(ANIMATED)
    argv = ["animate", str(script), "-o", str(tmp_path / "f.png"), "--frames", "0:3", "--samples", "1"]
    assert main([*argv, "--device", "cpu", "--video", str(tmp_path / "a.gif")]) == 0
    frames = sorted(p.name for p in tmp_path.glob("f_*.png"))
    assert frames == ["f_0000.png", "f_0001.png", "f_0002.png"] and (tmp_path / "a.gif").stat().st_size > 0
