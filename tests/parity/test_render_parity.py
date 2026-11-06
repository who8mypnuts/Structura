"""The precision engine renders the same image on every backend (docs/11 §8, integrator level)."""

from __future__ import annotations

from dataclasses import replace
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


@pytest.mark.parametrize("env", ["sunsky", "sunsky+rect", "sunsky+emitters"])
def test_backends_agree_with_an_environment_map_and_area_lights(cpu: CpuBackend, device: Any, env: str) -> None:
    """The environment-map and rect-light paths (CDF search, MIS, area sampling) on every backend."""
    extras = {"rect": "light r { type rect position [0 5 3] target [0 0 0] size [2 1] power 300 }\n",
              "emitters": "material lamp { emission #ffeecc 6 }\n{ y 3 s 0.5 } sphere::lamp\n"
                          "{ x 3 y 2 s 0.6 0.1 0.6 } box::lamp\n"}  # fmt: skip
    script = "#version 2\n" + SCRIPT + "".join(text for key, text in extras.items() if key in env)
    prepared = prepare(build_scene(compile_script(script).program).scene, tag_presets=True)
    settings = replace(_settings("path"), env_type="sunsky", backdrop_sky=True, sun_irradiance=(1.0, 1.0, 1.0))
    reference = render(prepared, settings, cpu).image
    image = render(prepared, settings, device).image
    close = np.abs(image - reference) < 2e-3
    assert float(reference.std()) > 0.02
    assert close.mean() > 0.98, f"{(~close).mean():.2%} of values differ"


V2_SOLIDS = """#version 2
set background #334
{ x -3 ry 30 color #e44 } cylinder
{ x -1.5 rx 40 color #4c4 } cone[0.3]
{ x 0 rx 60 color #48f } torus[0.3]
{ x 1.5 s 1 0.6 1.4 color #fb3 } ellipsoid
{ x 3 rz 40 color #c6f } tube[0.2]
"""


@pytest.mark.parametrize("integrator", ["preview", "path"])
def test_backends_agree_on_the_v2_solids(cpu: CpuBackend, device: Any, integrator: str) -> None:
    prepared = prepare(build_scene(compile_script(V2_SOLIDS).program).scene)
    reference = render(prepared, _settings(integrator), cpu).image
    image = render(prepared, _settings(integrator), device).image
    close = np.abs(image - reference) < 2e-3
    assert float(reference.std()) > 0.02
    assert close.mean() > 0.985, f"{(~close).mean():.2%} of values differ"


def test_every_primitive_kind_is_packed() -> None:
    kinds = set(pack_scene(_scene()).prim_u[:, 0].tolist())
    assert kinds == {0, 1, 2, 3, 4}  # box, sphere, capsule (line), triangle (mesh + triangle), grid
    solids = set(pack_scene(build_scene(compile_script(V2_SOLIDS).program).scene).prim_u[:, 0].tolist())
    assert solids == {2, 5, 6, 7}  # capsule (tube), ellipsoid, cylinder (+ cone), torus


def test_full_render_kernel_compiles_for_cuda() -> None:
    assert ".entry render_pass" in compile_ptx(render_module(), "compute_75")


PHOTON_SCENE = """#version 2
render { ground plane ground_offset 0.3 }
light key { type sun direction [-0.3 -1 -0.1] intensity 3 angle 0.5 }
set background #000
sphere::glass
{ x 1.5 } sphere::mirror
"""


def test_backends_agree_on_photon_caustics(cpu: CpuBackend, device: Any) -> None:
    """The photon pass and the gather (hash grid, BSDF) on every backend."""
    prepared = prepare(build_scene(compile_script(PHOTON_SCENE).program).scene, tag_presets=True)
    settings = replace(_settings("path"), caustics="photons", photon_count=50_000)
    reference = render(prepared, settings, cpu).image
    image = render(prepared, settings, device).image
    close = np.abs(image - reference) < 1e-2
    assert float(reference.std()) > 0.02
    assert close.mean() > 0.97, f"{(~close).mean():.2%} of values differ"


def test_aovs_agree_across_backends(cpu: CpuBackend, device: Any) -> None:
    """The AOV pass binds the whole scene buffer set while using part of it (an explicit wgpu layout)."""
    prepared = prepare(_scene(), tag_presets=True)
    settings = replace(_settings("path"), samples=1, samples_per_pass=1, aovs=True)
    reference, other = render(prepared, settings, cpu).aovs, render(prepared, settings, device).aovs
    assert reference is not None and other is not None
    assert (np.abs(reference.albedo - other.albedo) < 1e-3).mean() > 0.98
    assert (reference.instance == other.instance).mean() > 0.98


def test_aov_and_photon_kernels_compile_for_cuda() -> None:
    from structura.render.aovs import aov_module  # noqa: PLC0415
    from structura.render.photons import photon_module  # noqa: PLC0415

    assert ".entry aov_pass" in compile_ptx(aov_module(), "compute_75")
    assert ".entry photon_pass" in compile_ptx(photon_module(), "compute_75")
