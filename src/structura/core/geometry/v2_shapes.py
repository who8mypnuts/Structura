"""Tessellation of the EisenScript v2 primitives (docs/05 §9.6): cylinder, cone[r], torus[r], ellipsoid and
tube[r]. Shapes with a bracket parameter are grouped by its value, so each distinct shape is built once."""

from __future__ import annotations

import numpy as np

from ..scene.ir import PrimitiveKind as K
from ..scene.ir import SceneIR
from .trimesh import TriMesh, beams, instanced
from .unit_shapes import Mesh, unit_cylinder, unit_sphere, unit_torus

V2_KINDS = (K.CYLINDER, K.CONE, K.TORUS, K.ELLIPSOID, K.TUBE)


def tube_ends(xform: np.ndarray, params: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(a, b, world radius) of tubes: the line from (0,.5,.5) to (1,.5,.5), radius r/2 in object units."""
    linear, t = xform[:, :, :3], xform[:, :, 3]
    a = t + 0.5 * (linear[:, :, 1] + linear[:, :, 2])
    scale = 0.5 * (np.linalg.norm(linear[:, :, 1], axis=1) + np.linalg.norm(linear[:, :, 2], axis=1))
    return a, a + linear[:, :, 0], (0.5 * params * scale).astype(np.float32)


def unit_shape(kind: K, param: float, segments: int) -> Mesh:
    """The unit-cube mesh of a v2 kind (cone and torus shaped by their parameter)."""
    if kind == K.CONE:
        return unit_cylinder(segments, max(0.0, param))
    if kind == K.TORUS:
        return unit_torus(min(max(param, 1e-3), 1.0) / 2, max(8, segments // 2), segments)
    if kind == K.ELLIPSOID:
        return unit_sphere(max(8, segments // 2), segments)
    return unit_cylinder(segments)


def _tubes(x: np.ndarray, params: np.ndarray, rgba: np.ndarray, rows: np.ndarray, segments: int) -> TriMesh:
    """A cylinder between the ends plus a sphere at each end (the renderer's capsule)."""
    a, b, radius = tube_ends(x, params)
    linear, offset = beams(a, b, radius)
    ball = np.eye(3, dtype=np.float32)[None] * (2 * radius)[:, None, None]
    sphere = unit_sphere(max(8, segments // 2), segments)
    ends = [instanced(sphere, ball, p - radius[:, None], rgba, rows) for p in (a, b)]
    return TriMesh.concat([instanced(unit_cylinder(segments), linear, offset, rgba, rows), *ends])


def v2_kind_mesh(scene: SceneIR, kind: K, rows: np.ndarray, segments: int) -> TriMesh:
    x = scene.xform[rows].astype(np.float32)
    params, rgba = scene.params(rows), scene.rgba[rows]
    if kind == K.TUBE:
        return _tubes(x, params, rgba, rows, segments)
    groups = np.unique(params) if kind in (K.CONE, K.TORUS) else np.zeros(1, np.float32)
    parts = []
    for value in groups:
        take = params == value if kind in (K.CONE, K.TORUS) else np.ones(len(rows), bool)
        mesh = unit_shape(kind, float(value), segments)
        parts.append(instanced(mesh, x[take, :, :3], x[take, :, 3], rgba[take], rows[take]))
    return TriMesh.concat(parts)
