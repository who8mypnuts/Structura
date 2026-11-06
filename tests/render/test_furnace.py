"""White-furnace tests (docs/18 §5): in a uniform white environment, energy-conserving white materials
are invisible — every pixel converges to 1. Lossy ones must never exceed 1."""

from __future__ import annotations

from functools import cache

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.core.scene.material import Material
from structura.render.api import prepare, render
from structura.render.settings import RenderSettings

WHITE = (1.0, 1.0, 1.0)
CONSERVING = {
    "diffuse": Material(base=WHITE, roughness=1.0, specular=0.0),
    "mirror": Material(base=WHITE, metallic=1.0, roughness=0.0),
    "glass": Material(base=WHITE, transmission=1.0, roughness=0.0),
}
LOSSY = {
    "plastic": Material(base=WHITE, roughness=0.3),
    "rough-metal": Material(base=WHITE, metallic=1.0, roughness=0.7),
    "rough-glass": Material(base=WHITE, transmission=1.0, roughness=0.5),
    "coated": Material(base=WHITE, roughness=0.5, coat=1.0, coat_roughness=0.1),
}


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script("set background #fff\nsphere\n{ x 1.2 s 0.8 } box").program).scene


def _furnace(material: Material) -> np.ndarray:
    settings = RenderSettings(
        width=40,
        height=30,
        samples=64,
        samples_per_pass=64,
        integrator="path",
        max_bounces=24,
        sky_top=WHITE,
        sky_bottom=WHITE,
        sun_irradiance=(0.0, 0.0, 0.0),
        frame=True,
        clamp=1e6,
    )
    return render(prepare(_scene(), declared={"": material}), settings, CpuBackend()).image


@pytest.mark.parametrize("name", sorted(CONSERVING))
def test_energy_conserving_materials_vanish(name: str) -> None:
    image = _furnace(CONSERVING[name])
    assert float(image.mean()) == pytest.approx(1.0, abs=0.01)
    assert float(np.abs(image - 1.0).mean()) < 0.03


@pytest.mark.parametrize("name", sorted(LOSSY))
def test_lossy_materials_never_create_energy(name: str) -> None:
    image = _furnace(LOSSY[name])
    assert float(image.mean()) <= 1.01
    assert float(image.mean()) > 0.8  # and they do not lose absurd amounts either
