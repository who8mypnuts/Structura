"""v2 cameras and lights in the precision engine (docs/10 §4–5)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.render.api import render, script_settings

BASE = """#version 2
environment { type color color #000000 }
{ x -3 y -1 z -3 s 6 0.2 6 color #fff } box
{ y 0.5 color #fff } sphere
"""


def _image(extra: str, integrator: str = "path") -> np.ndarray:
    scene = build_scene(compile_script(BASE + extra).program).scene
    settings = script_settings(scene)
    from dataclasses import replace  # noqa: PLC0415

    settings = replace(settings, width=48, height=32, samples=8, samples_per_pass=8, integrator=integrator,
                       sun_irradiance=(0.0, 0.0, 0.0))  # fmt: skip
    return render(scene, settings, CpuBackend()).image


def test_point_and_spot_lights_illuminate_an_otherwise_black_scene() -> None:
    camera = "camera { position [0 3 6] target [0 0 0] fov 50 }\n"
    dark = _image(camera)
    lit = _image(camera + "light l { type point position [0 4 0] power 400 }\n")
    spot = _image(camera + "light s { type spot position [0 4 0] target [0 0 0] cone 10 power 400 }\n")
    assert float(dark.max()) < 1e-3
    assert float(lit.mean()) > 0.01 and 0.0 < float(spot.mean()) < float(lit.mean())  # the cone lights less


@pytest.mark.parametrize("camera", ["orthographic height 8", "spherical", "fisheye fov 180"])
def test_alternative_cameras_see_the_scene(camera: str) -> None:
    image = _image(f"camera {{ type {camera} position [0 3 6] target [0 0 0] }}\n", integrator="preview")
    assert np.isfinite(image).all() and float((image > 0.05).mean()) > 0.005


def test_rect_light_is_one_sided_and_matches_a_point_light_far_away() -> None:
    camera = "camera { position [0 3 6] target [0 0 0] fov 50 }\n"
    down = _image(camera + "light r { type rect position [0 4 0] target [0 0 0] size [1 1] power 400 }\n")
    up = _image(camera + "light r { type rect position [0 4 0] target [0 8 0] size [1 1] power 400 }\n")
    assert float(down.mean()) > 0.005 and float(up.max()) < 1e-3  # it only emits towards its target
    # A small rect light radiates like a Lambertian emitter: its on-axis irradiance is P/(π d²), i.e. 4× the
    # isotropic point light's P/(4π d²) – so the rect lights the floor under it more than the point light.
    point = _image(camera + "light l { type point position [0 4 0] power 400 }\n")
    centre = (slice(14, 18), slice(22, 26))
    assert float(down[centre].mean()) > 2.0 * float(point[centre].mean())
