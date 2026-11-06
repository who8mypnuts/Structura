"""Photon-mapped caustics (docs/10 §2.5)."""

from __future__ import annotations

from dataclasses import replace
from functools import cache

import numpy as np

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.api import launch_args, prepare_with_frame, progressive, script_settings
from structura.render.kernels import layout as lay
from structura.render.photons import add_photons, buckets, photon_map
from structura.render.settings import RenderSettings

SCRIPT = """#version 2
render { ground plane ground_offset 0.3 }
light key { type sun direction [0 -1 0] intensity 3 angle 0.5 }
camera { position [0 3 4] target [0.5 -0.2 0.5] fov 35 }
set background #000
sphere::glass
"""


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


def _settings(**changes: object) -> RenderSettings:
    base = replace(script_settings(_scene()), width=48, height=36, samples=8, samples_per_pass=8)
    return replace(base, **changes)  # type: ignore[arg-type]


def test_the_photons_carry_the_sunlight_the_sphere_refracts() -> None:
    settings = _settings(caustics="photons")
    prepared, frame = prepare_with_frame(_scene(), settings)
    args = launch_args(prepared, frame)
    stored = add_photons(args, prepared.lo, prepared.hi, 100_000, 0.0, CpuBackend(), 1)
    table = int(args["cfg"][lay.PHOTON_TABLE])
    photons = args["photon_f"][2 * table :].reshape(-1, lay.PHOTON_F)
    flux = photons[:, 3:6].sum(axis=0)
    geometric = 3.0 * np.pi * 0.5**2  # sun irradiance × the sphere's cross-section
    assert stored == len(photons) > 1000
    assert 0.6 * geometric < flux[0] < 1.0 * geometric  # minus Fresnel reflection and total internal reflection
    assert np.allclose(photons[:, 1], -0.3, atol=1e-4)  # stored on the ground, not on the glass


def test_every_photon_is_found_through_its_own_cell() -> None:
    rng = np.random.default_rng(3)
    photons = np.hstack([rng.uniform(-5, 5, (500, 3)), np.ones((500, 6))]).astype(np.float32)
    buffer, table = photon_map(photons, 0.1)
    sorted_photons = buffer[2 * table :].reshape(-1, lay.PHOTON_F)
    for p in photons[:20]:
        b = int(buckets(p[None, :3], 0.1, table)[0])
        start, count = int(buffer[2 * b]), int(buffer[2 * b + 1])
        cell = sorted_photons[start : start + count, :3]
        assert np.any(np.all(cell == p[:3], axis=1))


def test_photon_caustics_light_the_focus_inside_the_shadow() -> None:
    images = {}
    for mode in ("filtered", "photons"):
        settings = _settings(caustics=mode, photon_count=200_000, aovs=True)
        prepared, frame = prepare_with_frame(_scene(), settings)
        *_, last = progressive(prepared, settings, CpuBackend(), frame)
        images[mode] = last.image.mean(axis=-1)
    gain = images["photons"] - images["filtered"]
    assert gain.max() > 0.5  # a bright, focused spot …
    assert (gain > 0.05).mean() < 0.05  # … in a small part of the image


def test_render_blocks_choose_photon_caustics() -> None:
    text = "#version 2\nrender { caustics photons photon_count 5000 photon_radius 0.02 }\nsphere::glass\n"
    settings = script_settings(build_scene(compile_script(text).program).scene)
    assert (settings.caustics, settings.photon_count, settings.photon_radius) == ("photons", 5000, 0.02)
