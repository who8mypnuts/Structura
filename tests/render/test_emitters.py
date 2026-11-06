"""Emissive geometry as lights (docs/10 §4): next-event estimation + MIS is unbiased (matches the analytic
irradiance) and does not count emission twice."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.material import Material
from structura.render.api import prepare, render, script_settings
from structura.render.emitters import NO_EMITTER

WHITE_DIFFUSE = Material(base=(1.0, 1.0, 1.0), roughness=1.0, specular=0.0)
HEADER = "#version 2\nenvironment { type color color #000000 }\nmaterial lamp { emission #ffffff 4 }\n"
FLOOR = "{ s 20 0.1 20 } box\n"  # top face at y = 0.55 ('s' scales about the unit-cube centre)


def _centre(script: str, samples: int = 128) -> float:
    scene = build_scene(compile_script(HEADER + script + FLOOR).program).scene
    settings = replace(script_settings(scene), width=24, height=24, samples=samples, samples_per_pass=samples,
                       integrator="path", max_bounces=4, sun_irradiance=(0.0, 0.0, 0.0), clamp=1e6)  # fmt: skip
    image = render(prepare(scene, declared={"": WHITE_DIFFUSE}), settings, CpuBackend()).image
    return float(image[10:14, 10:14].mean())


def test_an_emissive_sphere_lights_the_floor_as_predicted() -> None:
    camera = "camera { position [3.5 4 3.5] target [0.5 0.55 0.5] fov 12 }\n"
    value = _centre(camera + "{ y 3 } sphere::lamp\n")  # centre (0.5, 3.5, 0.5), radius 0.5
    r, h = 0.5, 3.5 - 0.55
    assert value == pytest.approx(4.0 * (r / h) ** 2, rel=0.06)


def test_an_emissive_box_lights_the_floor_as_predicted() -> None:
    camera = "camera { position [3.5 4 3.5] target [0.5 0.55 0.5] fov 12 }\n"
    value = _centre(camera + "{ y 2.5 x 0 s 1 0.02 1 } box::lamp\n")  # a thin 1×1 slab, bottom at y ≈ 2.99
    h, half = 2.99 - 0.55, 0.5
    # Radiance of a white diffuse point under the centre of a Lambertian square (side 2a, height h, radiance L):
    # L · F with the point-to-square form factor F = (4/π) · a/√(a²+h²) · atan(a/√(a²+h²)).
    k = half / np.hypot(half, h)
    assert value == pytest.approx(4.0 * (4 / np.pi) * k * np.arctan(k), rel=0.08)


def test_emitters_are_packed_by_power() -> None:
    script = HEADER + "{ y 3 } sphere::lamp\n{ x 3 s 2 } sphere::lamp\n" + FLOOR
    prepared = prepare(build_scene(compile_script(script).program).scene, declared={"": WHITE_DIFFUSE})
    emitters = prepared.emitters
    assert len(emitters) == 2 and emitters.emit_cdf[-1] == pytest.approx(1.0)
    small, large = sorted(emitters.emit_f[:, 6])
    assert large == pytest.approx(4 * small, rel=1e-4)  # power ∝ area: the radius-1 sphere has 4× the area
    assert (emitters.prim_emit != NO_EMITTER).sum() == 2


def test_triangles_emit_too() -> None:
    glow = Material(base=(1.0, 1.0, 1.0), emission=(1.0, 0.9, 0.8), emission_strength=3.0)
    scene = build_scene(compile_script("triangle[0,0,0;1,0,0;0,1,0]\n{ y -1 s 4 0.1 4 } box\n").program).scene
    prepared = prepare(scene, declared={"": glow})
    kinds = sorted(prepared.emitters.emit_f[:, 0].tolist())
    assert kinds == [1.0, 2.0]  # the box and the triangle
    settings = replace(script_settings(scene), width=16, height=12, samples=4, samples_per_pass=4, frame=True)
    assert np.isfinite(render(prepared, settings, CpuBackend()).image).all()
