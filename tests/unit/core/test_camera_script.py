"""Copy Camera to Script and standard views (docs/08 §7, docs/07 §5)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.camera import Camera, standard_view
from structura.core.scene.camera_script import legacy_view, with_camera
from structura.core.scene.settings import settings_from_events
from structura.render.declarations import declared_camera

CAMERA = Camera((3.0, 4.0, 12.0), (0.5, -1.0, 0.2), (0.1, 1.0, 0.0), 35.0)


def _close(a: object, b: object) -> bool:
    return bool(np.allclose(np.asarray(a), np.asarray(b), atol=1e-4))


def test_the_legacy_view_is_the_exact_inverse() -> None:
    back = legacy_view(CAMERA).camera()
    assert _close(back.eye, CAMERA.eye) and _close(back.target, CAMERA.target)
    assert _close(back.up, CAMERA.basis[2]) and back.fov_y_deg == 35.0


def test_v1_lines_replace_the_old_ones_and_build_the_same_camera() -> None:
    text = "set maxdepth 10\nset translation [0 0 -20]\nset scale 0.5\nbox\n"
    new = with_camera(text, CAMERA, v2=False)
    assert new.count("set translation") == 1 and "set scale 0.5" not in new and "set maxdepth 10" in new
    assert with_camera(new, CAMERA, v2=False) == new  # idempotent
    camera = settings_from_events(build_scene(compile_script(new).program).scene.events).view.camera()
    assert _close(camera.eye, CAMERA.eye) and _close(camera.target, CAMERA.target)


def test_v2_block_goes_after_the_version_line() -> None:
    text = "#version 2\ncamera { position [1 2 3] target [0 0 0] }\nbox\n"
    new = with_camera(text, CAMERA, v2=True)
    assert new.startswith("#version 2\ncamera {") and new.count("camera {") == 1
    scene = build_scene(compile_script(new).program).scene
    camera = declared_camera(scene.declarations, Camera((0.0, 0.0, 1.0), (0.0, 0.0, 0.0)))
    assert camera is not None and _close(camera.eye, CAMERA.eye) and camera.fov_y_deg == 35.0


@pytest.mark.parametrize(("name", "axis"), [("front", 2), ("right", 0), ("top", 1)])
def test_standard_views_look_along_an_axis_at_the_centre(name: str, axis: int) -> None:
    lo, hi = np.array([0.0, 0.0, 0.0]), np.array([2.0, 4.0, 6.0])
    camera = standard_view(name, lo, hi, 1.5)
    offset = np.subtract(camera.eye, camera.target)
    assert _close(camera.target, (1.0, 2.0, 3.0)) and abs(offset[axis]) > 5 and _close(np.delete(offset, axis), 0)
