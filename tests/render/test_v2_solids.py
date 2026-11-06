"""The v2 solids in the precision engine agree with their tessellated meshes (docs/05 §9.6)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.geometry.tessellate import TessOptions, tessellate
from structura.core.lang.api import compile_script
from structura.core.scene.ir import PrimitiveKind, SceneIR
from structura.render.api import prepare, render
from structura.render.config import Frame
from structura.render.settings import RenderSettings

SETTINGS = RenderSettings(width=64, height=48, samples=4, samples_per_pass=4, integrator="preview", aovs=True)


def _scene(call: str) -> SceneIR:
    return build_scene(compile_script(f"#version 2\n{{ rx 35 ry 25 }} {call}\n").program).scene


def _as_triangles(scene: SceneIR) -> SceneIR:
    """The same shape as a soup of triangle[…] primitives (the tessellation at the finest level)."""
    mesh = tessellate(scene, TessOptions(lod="ultra"))
    corners = mesh.positions[mesh.indices].reshape(-1, 9)
    n = len(corners)
    xform = np.broadcast_to(np.eye(3, 4, dtype=np.float32), (n, 3, 4)).copy()
    aux = np.zeros((n, 13), np.float32)
    aux[:, :9] = corners
    return SceneIR(np.full(n, PrimitiveKind.TRIANGLE, np.uint8), xform, np.ones((n, 4), np.float32),
                   np.zeros(n, np.int32), np.zeros(n, np.int32), np.zeros(n, np.int32),
                   np.arange(n, dtype=np.int32), aux, ("",))  # fmt: skip


def _coverage(scene: SceneIR, frame_from: SceneIR) -> np.ndarray:
    fit = prepare(frame_from)
    prepared = prepare(scene)
    from structura.render.config import scene_frame  # noqa: PLC0415

    frame: Frame = scene_frame(fit.scene_settings, SETTINGS, fit.lo, fit.hi, None)
    aovs = render(prepared, SETTINGS, CpuBackend(), frame).aovs
    assert aovs is not None
    return aovs.alpha


@pytest.mark.parametrize("call", ["cylinder", "cone[0.4]", "torus[0.3]", "ellipsoid", "tube[0.3]"])
def test_analytic_silhouettes_match_the_tessellated_mesh(call: str) -> None:
    scene = _scene(call)
    analytic, meshed = _coverage(scene, scene), _coverage(_as_triangles(scene), scene)
    assert analytic.mean() > 0.02
    assert np.abs(analytic - meshed).mean() < 0.01, f"{call}: silhouettes differ"


def test_a_uniform_ellipsoid_is_a_sphere() -> None:
    sphere = build_scene(compile_script("#version 2\nsphere\n").program).scene
    ellipsoid = _scene("ellipsoid")
    assert np.abs(_coverage(sphere, sphere) - _coverage(build_scene(
        compile_script("#version 2\nellipsoid\n").program).scene, sphere)).mean() < 0.005  # fmt: skip
    assert len(ellipsoid) == 1
