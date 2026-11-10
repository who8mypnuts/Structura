"""Pack a SceneIR into flat render buffers (docs/09 §3.1, flat ABI docs/11 §2).

Every renderable thing becomes a *primitive* with a float record (PRIM_F floats) and an int record (PRIM_U
u32). The BVH is built over primitive world AABBs. Layouts (keep in sync with render/kernels/scene.py):

  prim_f: [0:12] inverse affine (world→object) rows   [12:16] linear rgba   [16:23] shape data   [23] generation
          sphere: centre xyz, radius   capsule: a xyz, b xyz, radius   triangle: unused
          cylinder: top radius ratio (1; cones less)   torus: tube radius (object units)
  prim_u: [0] kind   [1] material   [2] source instance row   [3] triangle row (tri_f) or 0
  tri_f:  9 floats per triangle (three world-space corners)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.color import srgb_to_linear
from ..core.geometry.triangles import scene_triangles
from ..core.geometry.v2_shapes import tube_ends
from ..core.scene.ir import PrimitiveKind as K
from ..core.scene.ir import SceneIR

PRIM_F, PRIM_U = 24, 4
RK_BOX, RK_SPHERE, RK_CAPSULE, RK_TRIANGLE, RK_GRID = 0, 1, 2, 3, 4
RK_ELLIPSOID, RK_CYLINDER, RK_TORUS = 5, 6, 7  # kernels/solids.py


@dataclass(frozen=True)
class PackOptions:
    line_radius: float = 0.01  # world units
    dot_radius: float = 0.05  # world units
    grid_width: float = 0.04  # fraction of the unit cube edge
    material_of_tag: np.ndarray | None = None  # int32[len(tags)] from a MaterialTable; None: material 0


@dataclass(frozen=True)
class PackedScene:
    prim_f: np.ndarray  # float32[P, 24]
    prim_u: np.ndarray  # uint32[P, 4]
    tri_f: np.ndarray  # float32[T, 9]
    lo: np.ndarray  # float32[P, 3] world AABB
    hi: np.ndarray  # float32[P, 3]

    def __len__(self) -> int:
        return int(self.prim_f.shape[0])


def inverse_rows(xform: np.ndarray) -> np.ndarray:
    """(N,3,4) object→world → (N,12) world→object rows. The inverse is the adjugate over the determinant:
    its rows are cross products of the columns (float64, vectorised; no per-matrix LU)."""
    linear, origin = xform[:, :, :3].astype(np.float64), xform[:, :, 3].astype(np.float64)
    a, b, c = linear[:, :, 0], linear[:, :, 1], linear[:, :, 2]
    adjugate = np.stack([np.cross(b, c), np.cross(c, a), np.cross(a, b)], axis=1)
    det = (a * adjugate[:, 0]).sum(axis=1)
    flat = np.abs(det) < 1e-18  # e.g. 's 1 1 0': give it a tiny thickness
    inverse = adjugate / np.where(flat, 1.0, det)[:, None, None]
    if flat.any():
        inverse[flat] = np.linalg.inv(linear[flat] + np.eye(3) * 1e-6)
    translation = -(inverse * origin[:, None, :]).sum(axis=2)
    return np.concatenate([inverse, translation[:, :, None]], axis=2).reshape(-1, 12).astype(np.float32)


def box_bounds(xform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """World AABBs of the unit cube's images: the origin plus the negative (positive) parts of each column."""
    linear, origin = xform[:, :, :3], xform[:, :, 3]
    lo = origin + np.minimum(linear, 0.0).sum(axis=2)
    hi = origin + np.maximum(linear, 0.0).sum(axis=2)
    return lo.astype(np.float32), hi.astype(np.float32)


@dataclass(frozen=True)
class _Ctx:
    scene: SceneIR
    opt: PackOptions

    def records(self, kind: int, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        f = np.zeros((len(rows), PRIM_F), np.float32)
        u = np.zeros((len(rows), PRIM_U), np.uint32)
        rgba = self.scene.rgba[rows]
        f[:, 12:15], f[:, 15] = srgb_to_linear(rgba[:, :3]), rgba[:, 3]
        f[:, 23] = self.scene.generation[rows]  # the debug_generation model
        by_tag = self.opt.material_of_tag
        u[:, 0], u[:, 2] = kind, rows
        u[:, 1] = by_tag[self.scene.tag[rows]] if by_tag is not None else 0
        return f, u


def _boxes(ctx: _Ctx, rows: np.ndarray, kind: int) -> tuple[np.ndarray, ...]:
    f, u = ctx.records(kind, rows)
    f[:, :12] = inverse_rows(ctx.scene.xform[rows])
    lo, hi = box_bounds(ctx.scene.xform[rows])
    return f, u, lo, hi


def _spheres(ctx: _Ctx, rows: np.ndarray, radius: float | None) -> tuple[np.ndarray, ...]:
    f, u = ctx.records(RK_SPHERE, rows)
    x = ctx.scene.xform[rows]
    centre = x[:, :, 3] + 0.5 * (x[:, :, 0] + x[:, :, 1] + x[:, :, 2])
    r = np.full(len(rows), radius, np.float32) if radius is not None else np.linalg.norm(0.5 * x[:, :, 2], axis=1)
    f[:, 16:19], f[:, 19] = centre, r
    return f, u, centre - r[:, None], centre + r[:, None]


def _capsules(ctx: _Ctx, rows: np.ndarray, radius: float | None) -> tuple[np.ndarray, ...]:
    """Lines (fixed world radius) and v2 tubes (radius from their parameter, radius None)."""
    f, u = ctx.records(RK_CAPSULE, rows)
    x = ctx.scene.xform[rows]
    if radius is None:
        a, b, r = tube_ends(x, ctx.scene.params(rows))
    else:
        a = x[:, :, 3] + 0.5 * (x[:, :, 1] + x[:, :, 2])
        b, r = a + x[:, :, 0], np.full(len(rows), radius, np.float32)
    f[:, 16:19], f[:, 19:22], f[:, 22] = a, b, r
    return f, u, np.minimum(a, b) - r[:, None], np.maximum(a, b) + r[:, None]


def _solids(ctx: _Ctx, rows: np.ndarray, kind: int, shape: np.ndarray | float) -> tuple[np.ndarray, ...]:
    """Ellipsoids, cylinders / cones and tori: intersected in object space like boxes."""
    f, u, lo, hi = _boxes(ctx, rows, kind)
    f[:, 16] = shape
    return f, u, lo, hi


def _triangles(ctx: _Ctx) -> tuple[np.ndarray, ...]:
    tri, owners = scene_triangles(ctx.scene)
    f, u = ctx.records(RK_TRIANGLE, owners)
    u[:, 3] = np.arange(len(owners), dtype=np.uint32)
    corners = tri.reshape(-1, 3, 3)
    return f, u, corners.min(axis=1), corners.max(axis=1), tri


def pack_scene(scene: SceneIR, options: PackOptions | None = None) -> PackedScene:
    opt = options or PackOptions()
    ctx = _Ctx(scene, opt)
    k = scene.kind
    rows = {kind: np.nonzero(k == kind)[0] for kind in K}
    parts = [
        _boxes(ctx, rows[K.BOX], RK_BOX),
        _boxes(ctx, rows[K.GRID], RK_GRID),
        _spheres(ctx, rows[K.SPHERE], None),
        _spheres(ctx, rows[K.DOT], opt.dot_radius),
        _capsules(ctx, rows[K.LINE], opt.line_radius),
        _capsules(ctx, rows[K.TUBE], None),
        _solids(ctx, rows[K.ELLIPSOID], RK_ELLIPSOID, 0.0),
        _solids(ctx, rows[K.CYLINDER], RK_CYLINDER, 1.0),
        _solids(ctx, rows[K.CONE], RK_CYLINDER, np.maximum(scene.params(rows[K.CONE]), 0.0)),
        _solids(ctx, rows[K.TORUS], RK_TORUS, np.clip(scene.params(rows[K.TORUS]), 1e-3, 1.0) / 2),
    ]
    f_t, u_t, lo_t, hi_t, tri = _triangles(ctx)
    parts.append((f_t, u_t, lo_t, hi_t))
    prim_f = np.concatenate([p[0] for p in parts]).astype(np.float32)
    prim_u = np.concatenate([p[1] for p in parts]).astype(np.uint32)
    lo = np.concatenate([p[2] for p in parts]).astype(np.float32)
    hi = np.concatenate([p[3] for p in parts]).astype(np.float32)
    prim_f[prim_u[:, 0] == RK_GRID, 16] = opt.grid_width
    return PackedScene(prim_f, prim_u, tri, lo, hi)
