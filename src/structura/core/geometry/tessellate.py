"""Vectorised, chunked tessellation of a SceneIR into triangle meshes (docs/15 §2.1).

World vertices for a chunk of instances come from one einsum; normals use the cofactor of each linear
part; winding flips automatically for mirrored instances (det < 0), which fixes 1.5's face-culling bug.
Lines become square beams, dots small spheres, grids twelve edge beams.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from ..scene.ir import PrimitiveKind as K
from ..scene.ir import SceneIR
from .triangles import scene_triangles
from .unit_shapes import Mesh, unit_box, unit_sphere

LOD = {"low": (8, 12), "medium": (12, 24), "high": (16, 32), "ultra": (32, 64)}  # sphere rings, segments
CHUNK = 65_536  # instances per chunk
GRID_EDGES = np.array(
    [[(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (1, 1, 0)], [(0, 0, 1), (1, 0, 1)], [(0, 1, 1), (1, 1, 1)],
     [(0, 0, 0), (0, 1, 0)], [(1, 0, 0), (1, 1, 0)], [(0, 0, 1), (0, 1, 1)], [(1, 0, 1), (1, 1, 1)],
     [(0, 0, 0), (0, 0, 1)], [(1, 0, 0), (1, 0, 1)], [(0, 1, 0), (0, 1, 1)], [(1, 1, 0), (1, 1, 1)]],
    np.float32,
)  # fmt: skip


@dataclass(frozen=True)
class TessOptions:
    lod: str = "medium"
    line_radius: float = 0.01  # world units (beam half-width)
    dot_radius: float = 0.05  # world units
    grid_width: float = 0.04  # fraction of the cube edge


@dataclass(frozen=True)
class TriMesh:
    positions: np.ndarray  # float32[V, 3]
    normals: np.ndarray  # float32[V, 3]
    colors: np.ndarray  # float32[V, 4] sRGB + alpha (the authored colour)
    indices: np.ndarray  # uint32[T, 3]
    owners: np.ndarray  # int64[T] SceneIR row of each triangle

    @property
    def triangles(self) -> int:
        return int(self.indices.shape[0])

    @classmethod
    def empty(cls) -> TriMesh:
        z = np.zeros((0, 3), np.float32)
        return cls(z, z, np.zeros((0, 4), np.float32), np.zeros((0, 3), np.uint32), np.zeros(0, np.int64))

    @classmethod
    def concat(cls, parts: list[TriMesh]) -> TriMesh:
        parts = [p for p in parts if p.triangles]
        if not parts:
            return cls.empty()
        offsets = np.cumsum([0] + [len(p.positions) for p in parts[:-1]])
        return cls(
            np.concatenate([p.positions for p in parts]),
            np.concatenate([p.normals for p in parts]),
            np.concatenate([p.colors for p in parts]),
            np.concatenate([p.indices + np.uint32(o) for p, o in zip(parts, offsets, strict=True)]),
            np.concatenate([p.owners for p in parts]),
        )


def cofactor(linear: np.ndarray) -> np.ndarray:
    """(N,3,3) cofactor matrices: transform normals, stay finite for singular (flat) instances."""
    a, b, c = linear[:, :, 0], linear[:, :, 1], linear[:, :, 2]
    return np.stack([np.cross(b, c), np.cross(c, a), np.cross(a, b)], axis=2)


def _normalise(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    out: np.ndarray = np.where(n > 1e-30, v / np.maximum(n, 1e-30), np.array([0, 0, 1], np.float32))
    return out.astype(np.float32)


def instanced(mesh: Mesh, linear: np.ndarray, offset: np.ndarray, colors: np.ndarray, rows: np.ndarray) -> TriMesh:
    """Place ``mesh`` with per-instance affine (linear (N,3,3), offset (N,3)); one colour per instance."""
    n, v = len(rows), len(mesh.positions)
    if n == 0:
        return TriMesh.empty()
    pos = np.einsum("nij,vj->nvi", linear, mesh.positions) + offset[:, None, :]
    nrm = _normalise(np.einsum("nij,vj->nvi", cofactor(linear), mesh.normals))
    flip = np.linalg.det(linear) < 0
    tri = np.broadcast_to(mesh.indices, (n, *mesh.indices.shape)).copy()
    tri[flip] = tri[flip][:, :, ::-1]
    tri = tri + (np.arange(n, dtype=np.uint32) * np.uint32(v))[:, None, None]
    cols = np.repeat(colors.astype(np.float32), v, axis=0)
    owners = np.repeat(rows.astype(np.int64), mesh.triangles)
    return TriMesh(pos.reshape(-1, 3).astype(np.float32), nrm.reshape(-1, 3), cols, tri.reshape(-1, 3), owners)


def _beams(a: np.ndarray, b: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Affines mapping the unit cube onto square beams from a to b (N,3) with half-width radius (N,)."""
    axis = b - a
    length = np.linalg.norm(axis, axis=1, keepdims=True)
    d = axis / np.maximum(length, 1e-30)
    helper = np.where(np.abs(d[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    u = _normalise(np.cross(d, helper))
    w = np.cross(d, u)
    r = radius[:, None]
    linear = np.stack([axis, 2 * r * u, 2 * r * w], axis=2).astype(np.float32)
    return linear, (a - r * u - r * w).astype(np.float32)


def _kind_mesh(scene: SceneIR, kind: K, rows: np.ndarray, opt: TessOptions) -> TriMesh:
    x = scene.xform[rows].astype(np.float32)
    linear, t, rgba = x[:, :, :3], x[:, :, 3], scene.rgba[rows]
    if kind == K.BOX:
        return instanced(unit_box(), linear, t, rgba, rows)
    if kind in (K.SPHERE, K.DOT):
        centre = t + 0.5 * linear.sum(axis=2)
        r = np.linalg.norm(0.5 * linear[:, :, 2], axis=1) if kind == K.SPHERE else np.full(len(rows), opt.dot_radius)
        scale = np.eye(3, dtype=np.float32)[None] * (2 * r)[:, None, None]
        return instanced(unit_sphere(*LOD[opt.lod]), scale, centre - r[:, None], rgba, rows)
    if kind == K.LINE:
        a = t + 0.5 * (linear[:, :, 1] + linear[:, :, 2])
        lin, off = _beams(a, a + linear[:, :, 0], np.full(len(rows), opt.line_radius, np.float32))
        return instanced(unit_box(), lin, off, rgba, rows)
    return _grid(linear, t, rgba, rows, opt)


def _grid(linear: np.ndarray, t: np.ndarray, rgba: np.ndarray, rows: np.ndarray, opt: TessOptions) -> TriMesh:
    ends = np.einsum("nij,ekj->neki", linear, GRID_EDGES) + t[:, None, None, :]  # (N, 12, 2, 3)
    size = np.linalg.norm(linear, axis=1).max(axis=1) * opt.grid_width * 0.5
    a, b = ends[:, :, 0].reshape(-1, 3), ends[:, :, 1].reshape(-1, 3)
    lin, off = _beams(a, b, np.repeat(size, 12).astype(np.float32))
    return instanced(unit_box(), lin, off, np.repeat(rgba, 12, axis=0), np.repeat(rows, 12))


def _triangle_mesh(scene: SceneIR) -> TriMesh:
    corners, owners = scene_triangles(scene)
    if not len(owners):
        return TriMesh.empty()
    p = corners.reshape(-1, 3, 3)
    n = _normalise(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]))
    normals = np.repeat(n, 3, axis=0)
    colors = np.repeat(scene.rgba[owners].astype(np.float32), 3, axis=0)
    indices = np.arange(3 * len(owners), dtype=np.uint32).reshape(-1, 3)
    return TriMesh(p.reshape(-1, 3).astype(np.float32), normals, colors, indices, owners)


def iter_tessellate(scene: SceneIR, opt: TessOptions | None = None, chunk: int = CHUNK) -> Iterator[TriMesh]:
    """Triangle meshes in chunks of ≤ ``chunk`` instances, kind by kind (emission order within a kind)."""
    o = opt or TessOptions()
    for kind in (K.BOX, K.SPHERE, K.DOT, K.LINE, K.GRID):
        rows = np.nonzero(scene.kind == kind)[0]
        for start in range(0, len(rows), chunk):
            yield _kind_mesh(scene, kind, rows[start : start + chunk], o)
    yield _triangle_mesh(scene)


def tessellate(scene: SceneIR, opt: TessOptions | None = None) -> TriMesh:
    return TriMesh.concat(list(iter_tessellate(scene, opt)))
