"""Shared export geometry: tessellation and TRS decomposition (docs/15 §2)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.geometry.affine import compose, decompose
from structura.core.geometry.tessellate import TessOptions, tessellate
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR


def _scene(text: str) -> SceneIR:
    return build_scene(compile_script(text).program).scene


def _volume(text: str, lod: str = "medium") -> float:
    m = tessellate(_scene(text), TessOptions(lod=lod))
    p, i = m.positions.astype(np.float64), m.indices
    return float(np.einsum("ij,ij->i", p[i[:, 0]], np.cross(p[i[:, 1]], p[i[:, 2]])).sum() / 6)


def test_boxes_are_closed_and_outward_even_when_mirrored() -> None:
    assert _volume("box") == pytest.approx(1.0)
    assert _volume("{ fx } box") == pytest.approx(1.0)  # winding flipped for det < 0
    assert _volume("{ s 2 1 3 } box") == pytest.approx(6.0)


def test_spheres_converge_to_the_inscribed_sphere() -> None:
    assert _volume("sphere", "ultra") == pytest.approx(np.pi / 6, rel=0.01)


def test_every_kind_produces_triangles_owned_by_its_row() -> None:
    scene = _scene("box\nsphere\ngrid\n{ s 2 0.1 0.1 } line\ndot\ntriangle[0,0,0;1,0,0;0,1,0]")
    mesh = tessellate(scene)
    assert set(np.unique(mesh.owners).tolist()) == set(range(len(scene)))
    assert np.isfinite(mesh.normals).all() and np.allclose(np.linalg.norm(mesh.normals, axis=1), 1, atol=1e-4)


def test_trs_round_trips_and_flags_shear() -> None:
    scene = _scene("{ rx 30 ry 20 s 1 2 3 } box\n{ fx rz 45 } box\n{ s 1 2 1 rz 30 } box")
    trs = decompose(scene.xform)
    assert trs.representable().tolist() == [True, True, False]
    back = compose(trs)
    assert np.abs(back[:2] - scene.xform[:2]).max() < 1e-5
