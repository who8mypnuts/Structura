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


def test_animate_a_project_follows_its_timeline(tmp_path: Path) -> None:
    from structura.core.animation.timeline import Interp, Timeline  # noqa: PLC0415
    from structura.core.project.model import Project, save  # noqa: PLC0415

    text = "#version 2\n#param k float = 0 range 0..4\nrender { integrator preview size 24x16 }\nbox\n{ y k } box\n"
    timeline = Timeline(fps=12, start=0, end=2).set_key("param:k", 0, 0.0, Interp.LINEAR).set_key("param:k", 2, 4.0)
    save(tmp_path / "a.structura", Project(text, timeline=timeline))
    argv = ["animate", str(tmp_path / "a.structura"), "-o", str(tmp_path / "f.png"), "--samples", "1"]
    assert main([*argv, "--device", "cpu"]) == 0
    images = [np.asarray(Image.open(tmp_path / f"f_{i:04d}.png")) for i in range(3)]
    assert not np.array_equal(images[0], images[2])  # the second box moved away from the first


def test_build_frame_applies_keys_seed_and_frame_variables() -> None:
    from structura.core.animation.timeline import Interp, Timeline  # noqa: PLC0415
    from structura.render.animation import Animation, build_frame  # noqa: PLC0415

    text = "#version 2\n#param k float = 0 range 0..4\n{ x k rz (frame * 10) } box\n"
    tl = Timeline().set_key("param:k", 0, 0.0, Interp.LINEAR).set_key("param:k", 10, 2.0).set_key("seed", 0, 7)
    scene, seed = build_frame(Animation(text, tl), 5)
    moved, _ = build_frame(Animation(text, tl), 10)
    assert seed == 7 and float(moved.xform[0, 0, 3]) > float(scene.xform[0, 0, 3])  # k: 1 → 2
    assert np.isclose(scene.xform[0, 0, 0], np.cos(np.radians(50)), atol=1e-6)  # 'rz (frame * 10)' at frame 5


def test_animate_turntable_loops_around_the_structure(tmp_path: Path) -> None:
    script = tmp_path / "still.es"
    script.write_text("#version 2\nrender { integrator preview size 24x16 }\n{ x 1 } box\n{ s 0.5 } sphere\n")
    argv = ["animate", str(script), "-o", str(tmp_path / "t.png"), "--samples", "1", "--fps", "8"]
    assert main([*argv, "--device", "cpu", "--turntable", "0.5"]) == 0
    images = [np.asarray(Image.open(tmp_path / f"t_{i:04d}.png")) for i in range(4)]
    assert not (tmp_path / "t_0004.png").exists()  # 0.5 s at 8 fps: four frames, one loop
    assert not np.array_equal(images[0], images[2])  # half a turn: the box is on the other side


def test_turntable_and_saved_view_paths() -> None:
    from structura.core.animation.camera import camera_at  # noqa: PLC0415
    from structura.core.animation.paths import Turntable, path_through, turntable  # noqa: PLC0415
    from structura.core.animation.timeline import Timeline  # noqa: PLC0415
    from structura.core.scene.camera import Camera  # noqa: PLC0415

    base = Camera((0.0, 3.0, 10.0), (0.0, 1.0, 0.0))
    tl = turntable(Timeline().set_key("camera:fov", 0, 30.0), base, Turntable(frames=8, elevation_deg=0.0))
    assert (tl.start, tl.end) == (0, 7) and tl.track("camera:fov") is not None  # lens tracks stay
    eyes = [np.asarray(camera_at(tl, f, base).eye) for f in range(8)]
    radii = [np.linalg.norm((e - base.target)[[0, 2]]) for e in eyes]
    assert np.allclose(radii, radii[0]) and np.allclose([e[1] for e in eyes], 1.0)  # a level circle
    np.testing.assert_allclose(eyes[4], [0.0, 1.0, -np.hypot(10.0, 2.0)], atol=1e-9)  # half way round
    views = [base, Camera((10.0, 3.0, 0.0), (0.0, 0.0, 0.0), fov_y_deg=50.0)]
    path = path_through(Timeline(), views, 24, start=10)
    assert (path.start, path.end) == (10, 34) and camera_at(path, 34, base).fov_y_deg == 50.0
    assert path_through(Timeline(), views[:1], 24) == Timeline()  # one view is no path
    eased = turntable(Timeline(), base, Turntable(frames=9, turns=0.5, ease=True, zoom=0.5))
    ends = [np.asarray(camera_at(eased, f, base).eye) - base.target for f in (0, 8)]
    np.testing.assert_allclose(ends[1], ends[0] * [-0.5, 0.5, -0.5], atol=1e-9)  # half a turn, half the distance
    steps = [np.linalg.norm(np.asarray(camera_at(eased, f + 1, base).eye) - camera_at(eased, f, base).eye)
             for f in range(8)]  # fmt: skip
    assert steps[0] < steps[4] and steps[7] < steps[4]  # gentle start and stop
