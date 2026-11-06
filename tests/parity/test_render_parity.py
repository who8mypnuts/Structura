"""The precision engine renders the same image on every backend (docs/11 §8, integrator level)."""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.compute.cuda import compile_ptx
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.api import prepare, render, render_module
from structura.render.pack import pack_scene
from structura.render.settings import RenderSettings

SCRIPT = """
set background #334
set raytracer::reflection 0.3
set raytracer::gold::phong [0.4,0.8,0.9]
{ x -2 } box::gold
{ x 0 s 1.5 } sphere::glass
{ x 0 z -2 s 1.5 alpha 0.5 color #f80 } sphere
{ x 2 color #8cf } grid::plastic
{ y 2 s 2 0.1 0.1 } line
{ y -2 } dot
{ z 2 s 0.5 color #fc8 } mesh_chain
{ x -2 y 2 } triangle[0,0,0;1,0,0;0,1,0]
rule mesh_chain md 4 { { x 1 rz 20 } mesh_chain mesh }
"""


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


def _settings(integrator: str) -> RenderSettings:
    return RenderSettings(
        width=48,
        height=36,
        samples=2,
        samples_per_pass=2,
        integrator=integrator,
        frame=True,
        ao_samples=4,
        max_bounces=3,
    )


@pytest.mark.parametrize("integrator", ["preview", "ao", "path", "classic"])
def test_backends_agree(cpu: CpuBackend, device: Any, integrator: str) -> None:
    prepared = prepare(_scene(), tag_presets=True)
    reference = render(prepared, _settings(integrator), cpu).image
    image = render(prepared, _settings(integrator), device).image
    close = np.abs(image - reference) < 2e-3
    assert float(reference.std()) > 0.02  # the scene is actually visible
    assert close.mean() > 0.985, f"{(~close).mean():.2%} of values differ"  # edge pixels may flip on float noise


def test_every_primitive_kind_is_packed() -> None:
    kinds = set(pack_scene(_scene()).prim_u[:, 0].tolist())
    assert kinds == {0, 1, 2, 3, 4}  # box, sphere, capsule (line), triangle (mesh + triangle), grid


def test_full_render_kernel_compiles_for_cuda() -> None:
    assert ".entry render_pass" in compile_ptx(render_module(), "compute_75")
