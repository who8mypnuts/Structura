"""Vectorised, chunked tessellation of a SceneIR into triangle meshes (docs/15 §2.1).

World vertices for a chunk of instances come from one einsum; normals use the cofactor of each linear
part; winding flips automatically for mirrored instances (det < 0), which fixes 1.5's face-culling bug.
Lines become square beams, dots small spheres, grids twelve edge beams; the v2 shapes come from v2_shapes.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from ..scene.ir import PrimitiveKind as K
from ..scene.ir import SceneIR
from .triangles import scene_triangles
from .trimesh import TriMesh, beams, instanced, normalise
from .unit_shapes import unit_box, unit_sphere
from .v2_shapes import V2_KINDS, v2_kind_mesh

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

    @property
    def segments(self) -> int:
        """Segments around round v2 shapes (cylinders, cones, tori, tubes)."""
        return LOD[self.lod][1]


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
        lin, off = beams(a, a + linear[:, :, 0], np.full(len(rows), opt.line_radius, np.float32))
        return instanced(unit_box(), lin, off, rgba, rows)
    if kind in V2_KINDS:
        return v2_kind_mesh(scene, kind, rows, opt.segments)
    return _grid(linear, t, rgba, rows, opt)


def _grid(linear: np.ndarray, t: np.ndarray, rgba: np.ndarray, rows: np.ndarray, opt: TessOptions) -> TriMesh:
    ends = np.einsum("nij,ekj->neki", linear, GRID_EDGES) + t[:, None, None, :]  # (N, 12, 2, 3)
    size = np.linalg.norm(linear, axis=1).max(axis=1) * opt.grid_width * 0.5
    a, b = ends[:, :, 0].reshape(-1, 3), ends[:, :, 1].reshape(-1, 3)
    lin, off = beams(a, b, np.repeat(size, 12).astype(np.float32))
    return instanced(unit_box(), lin, off, np.repeat(rgba, 12, axis=0), np.repeat(rows, 12))


def _triangle_mesh(scene: SceneIR) -> TriMesh:
    corners, owners = scene_triangles(scene)
    if not len(owners):
        return TriMesh.empty()
    p = corners.reshape(-1, 3, 3)
    n = normalise(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]))
    normals = np.repeat(n, 3, axis=0)
    colors = np.repeat(scene.rgba[owners].astype(np.float32), 3, axis=0)
    indices = np.arange(3 * len(owners), dtype=np.uint32).reshape(-1, 3)
    return TriMesh(p.reshape(-1, 3).astype(np.float32), normals, colors, indices, owners)


def iter_tessellate(scene: SceneIR, opt: TessOptions | None = None, chunk: int = CHUNK) -> Iterator[TriMesh]:
    """Triangle meshes in chunks of ≤ ``chunk`` instances, kind by kind (emission order within a kind)."""
    o = opt or TessOptions()
    for kind in (K.BOX, K.SPHERE, K.DOT, K.LINE, K.GRID, *V2_KINDS):
        rows = np.nonzero(scene.kind == kind)[0]
        for start in range(0, len(rows), chunk):
            yield _kind_mesh(scene, kind, rows[start : start + chunk], o)
    yield _triangle_mesh(scene)


def tessellate(scene: SceneIR, opt: TessOptions | None = None) -> TriMesh:
    return TriMesh.concat(list(iter_tessellate(scene, opt)))
