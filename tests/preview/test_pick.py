"""Exact CPU picking (docs/08 §6, §9)."""

from __future__ import annotations

import numpy as np

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.camera import Camera
from structura.preview.pick import camera_ray, pick

SCENE = build_scene(compile_script("3 * { x 2 } box\n{ y 3 s 0.5 } sphere\n").program).scene


def test_the_ray_through_the_centre_picks_the_box_in_front() -> None:
    camera = Camera((4.5, 0.5, 10.0), (4.5, 0.5, 0.0))  # the boxes span x 2…3, 4…5, 6…7; this is the middle one
    origin, direction = camera_ray(camera, (200, 100), 99.5, 49.5)
    assert np.allclose(direction, (0.0, 0.0, -1.0), atol=1e-3)
    hit = pick(SCENE, origin, direction)
    assert hit is not None and hit[0] == 1 and abs(origin[2] + hit[1] * direction[2] - 1.0) < 1e-3  # front face z=1


def test_misses_and_nearest_hits() -> None:
    assert pick(SCENE, np.array([0.5, -5.0, 0.5]), np.array([1.0, 0.0, 0.0])) is None
    hit = pick(SCENE, np.array([-5.0, 0.5, 0.5]), np.array([1.0, 0.0, 0.0]))  # along the row of boxes
    assert hit is not None and hit[0] == 0 and np.isclose(hit[1], 7.0)
