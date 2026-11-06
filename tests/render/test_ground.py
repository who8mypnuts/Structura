"""Ground plane and shadow catcher (docs/10 §2.3)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.material import MaterialModel
from structura.render.api import prepare, prepare_with_frame, progressive, script_settings
from structura.render.ground import Ground
from structura.render.settings import RenderSettings

SCRIPT = "set background #fff\n{ y 1 } sphere\n"
BASE = RenderSettings(width=40, height=30, samples=32, samples_per_pass=8, integrator="path", frame=True, aovs=True)


def _render(settings: RenderSettings):  # type: ignore[no-untyped-def]
    scene = build_scene(compile_script(SCRIPT).program).scene
    prepared, frame = prepare_with_frame(scene, settings)
    *_, last = progressive(prepared, settings, CpuBackend(), frame)
    return last, len(scene)


def test_the_ground_is_one_more_primitive_and_material_outside_the_framing_bounds() -> None:
    scene = build_scene(compile_script(SCRIPT).program).scene
    plain, grounded = prepare(scene), prepare(scene, ground=Ground(catcher=True))
    assert len(grounded.packed) == len(plain.packed) + 1
    assert grounded.materials.materials[-1].model == MaterialModel.SHADOW_CATCHER
    assert np.array_equal(plain.lo, grounded.lo) and np.array_equal(plain.hi, grounded.hi)
    assert float(grounded.packed.hi[-1, 1]) == np.float32(plain.lo[1])  # the top face touches the structure


def test_a_ground_plane_is_seen_below_the_structure() -> None:
    result, n = _render(replace(BASE, ground_plane="plane"))
    assert result.aovs is not None
    ground = result.aovs.instance == n
    assert ground[-1].mean() > 0.9 and not ground[0].any()  # the bottom row is ground, the top row is sky


def test_the_shadow_catcher_shows_the_background_with_shadows() -> None:
    result, n = _render(replace(BASE, ground_plane="catcher", samples=64))
    assert result.aovs is not None
    ground = (result.aovs.instance == n) & (result.aovs.alpha > 0.99)
    lum = result.image[ground] @ np.array([0.2126, 0.7152, 0.0722])
    assert ground.sum() > 50
    assert np.median(lum) > 0.9  # most of the catcher is the white background …
    assert lum.min() < 0.6  # … except where the sphere's shadow falls


def test_script_render_blocks_set_the_ground() -> None:
    text = "#version 2\nrender { ground catcher ground_color #808080 ground_offset 0.5 }\nsphere\n"
    settings = script_settings(build_scene(compile_script(text).program).scene)
    assert settings.ground_plane == "catcher" and settings.ground_offset == 0.5
    assert abs(settings.ground_color[0] - 128 / 255) < 1e-3
    assert settings.ground_spec == Ground(True, settings.ground_color, 0.5)
