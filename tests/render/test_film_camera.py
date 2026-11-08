"""Reconstruction filters (filter importance sampling), region render and polygonal bokeh (docs/09 §6, docs/10 §5)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.material import Material
from structura.render.api import prepare, render, script_settings
from structura.render.filters import FILTERS, filter_table
from structura.render.settings import FILTER_NAMES, RenderSettings

WHITE = (1.0, 1.0, 1.0)


def test_every_filter_has_a_table_and_negative_lobes_are_signed() -> None:
    assert set(FILTERS) == set(FILTER_NAMES)
    for name in FILTER_NAMES:
        table, radius = filter_table(name)
        inverse, signs = table[:257], table[257:]
        assert np.all(np.diff(inverse) >= -1e-6) and inverse[0] >= -radius - 1e-6 and inverse[-1] <= radius + 1e-6
        assert ((signs < 0).any()) == (name in ("mitchell", "catmull-rom", "lanczos", "sinc")), name


@pytest.mark.parametrize(("name", "tolerance"), [("gaussian", 0.02), ("mitchell", 0.02), ("lanczos", 0.05)])
def test_filtered_furnace_stays_white(name: str, tolerance: float) -> None:
    """Signed filter weights are normalised: a constant image stays constant. (Lanczos's large negative
    lobes make the ratio estimator noisier at low sample counts; it is consistent as samples grow.)"""
    scene = build_scene(compile_script("set background #fff\nsphere").program).scene
    settings = RenderSettings(width=24, height=18, samples=16, samples_per_pass=16, integrator="path", frame=True,
                              sky_top=WHITE, sky_bottom=WHITE, sun_irradiance=(0.0, 0.0, 0.0), max_bounces=8,
                              filter=name, backdrop_sky=True, clamp=1e6)  # fmt: skip
    white = Material(base=WHITE, roughness=1.0, specular=0.0)
    image = render(prepare(scene, declared={"": white}), settings, CpuBackend()).image
    assert float(image.mean()) == pytest.approx(1.0, abs=tolerance)


def test_region_render_only_touches_the_region() -> None:
    scene = build_scene(compile_script("{ s 2 } box\nsphere").program).scene
    base = RenderSettings(width=32, height=24, samples=4, samples_per_pass=4, integrator="preview", frame=True)
    full = render(prepare(scene), base, CpuBackend()).image
    part = render(prepare(scene), replace(base, region=(8, 6, 20, 16)), CpuBackend()).image
    inside = (slice(6, 16), slice(8, 20))
    assert np.allclose(part[inside], full[inside])
    mask = np.ones(part.shape[:2], bool)
    mask[inside] = False
    assert float(np.abs(part[mask]).max()) == 0.0


def test_polygonal_bokeh_keeps_the_energy_but_changes_the_blur() -> None:
    camera = "camera { position [0 0 8] target [0 0 0] fov 20 aperture 0.4 focus 3 }"
    script = ("#version 2\nenvironment { type color color #000000 }\nmaterial lamp { emission #fff 20 }\n"
              f"{camera}\n{{ s 0.3 }} sphere::lamp\n")  # fmt: skip
    scene = build_scene(compile_script(script).program).scene
    base = replace(script_settings(scene), width=48, height=48, samples=256, samples_per_pass=64, integrator="path")
    round_ = render(prepare(scene), base, CpuBackend()).image
    hexagon = render(prepare(scene), replace(base, blades=6, blade_rotation_deg=15.0), CpuBackend()).image
    assert float(hexagon.sum()) == pytest.approx(float(round_.sum()), rel=0.05)  # the same light, spread differently
    lit_round, lit_hexagon = ((img.mean(axis=2) > 0.05).sum() for img in (round_, hexagon))
    assert 0.75 < lit_hexagon / lit_round < 0.95  # an inscribed hexagon covers 83% of the disc
