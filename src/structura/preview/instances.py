"""SceneIR → per-pipeline instance arrays for the preview engine (docs/08 §3).

Per instance: the 3×4 affine as three row vec4s (48 B), sRGB colour + alpha as RGBA8 (4 B) and the SceneIR
row + 1 as the pick id (4 B). Colour precision is 8 bits by design: this is the *preview* engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.geometry.triangles import scene_triangles
from ..core.scene.ir import PrimitiveKind as K
from ..core.scene.ir import SceneIR


@dataclass(frozen=True)
class Batch:
    rows: np.ndarray  # float32[N, 12]: affine rows
    colors: np.ndarray  # uint8[N, 4]
    ids: np.ndarray  # uint32[N]

    def __len__(self) -> int:
        return int(self.ids.shape[0])

    def split(self) -> tuple[Batch, Batch]:
        """(opaque, see-through) instances."""
        see = self.colors[:, 3] < 255
        return Batch(self.rows[~see], self.colors[~see], self.ids[~see]), Batch(
            self.rows[see], self.colors[see], self.ids[see]
        )


@dataclass(frozen=True)
class TriangleSoup:
    vertices: np.ndarray  # float32[3T, 6]: position, normal
    colors: np.ndarray  # uint8[3T, 4]
    ids: np.ndarray  # uint32[3T]

    def __len__(self) -> int:
        return int(self.ids.shape[0]) // 3

    def split(self) -> tuple[TriangleSoup, TriangleSoup]:
        see = self.colors[:, 3] < 255
        return (
            TriangleSoup(self.vertices[~see], self.colors[~see], self.ids[~see]),
            TriangleSoup(self.vertices[see], self.colors[see], self.ids[see]),
        )


@dataclass(frozen=True)
class PreviewScene:
    boxes: tuple[Batch, Batch, Batch]  # by orientation: right-handed, mirrored, flat (singular)
    spheres: Batch
    dots: Batch
    lines: Batch
    grids: Batch
    triangles: TriangleSoup
    lo: np.ndarray
    hi: np.ndarray
    feature_size: float  # median instance size (drives SSAO radius and line widths)

    @property
    def instances(self) -> int:
        batches = (*self.boxes, self.spheres, self.dots, self.lines, self.grids)
        return sum(len(b) for b in batches) + len(self.triangles)


def _colors(scene: SceneIR, rows: np.ndarray) -> np.ndarray:
    out: np.ndarray = np.clip(np.rint(scene.rgba[rows] * 255.0), 0, 255).astype(np.uint8)
    return out


def _rows_batch(scene: SceneIR, rows: np.ndarray) -> Batch:
    affine = np.ascontiguousarray(scene.xform[rows].reshape(-1, 12), np.float32)
    return Batch(affine, _colors(scene, rows), (rows + 1).astype(np.uint32))


def _batch(scene: SceneIR, kind: K) -> Batch:
    return _rows_batch(scene, np.nonzero(scene.kind == kind)[0])


def _oriented_boxes(scene: SceneIR) -> tuple[Batch, Batch, Batch]:
    """Boxes split by det(M): back faces can then be culled (thin slabs no longer z-fight with themselves)."""
    rows = np.nonzero(scene.kind == K.BOX)[0]
    det = np.linalg.det(scene.xform[rows, :, :3].astype(np.float64)) if rows.size else np.zeros(0)
    scale = np.abs(scene.xform[rows, :, :3]).max(axis=(1, 2)) ** 3 if rows.size else np.zeros(0)
    flat = np.abs(det) <= 1e-9 * np.maximum(scale, 1e-30)
    return (
        _rows_batch(scene, rows[(det > 0) & ~flat]),
        _rows_batch(scene, rows[(det < 0) & ~flat]),
        _rows_batch(scene, rows[flat]),
    )


def _triangles(scene: SceneIR) -> TriangleSoup:
    corners, owners = scene_triangles(scene)
    p = corners.reshape(-1, 3, 3)
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-20)
    vertices = np.concatenate([p, np.repeat(n[:, None], 3, axis=1)], axis=2).reshape(-1, 6).astype(np.float32)
    owner3 = np.repeat(owners, 3)
    return TriangleSoup(vertices, _colors(scene, owner3), (owner3 + 1).astype(np.uint32))


def _bounds(scene: SceneIR) -> tuple[np.ndarray, np.ndarray, float]:
    drawn = scene.kind != K.TEMPLATE
    if not drawn.any():
        return np.full(3, -1.0), np.full(3, 1.0), 0.1
    x = scene.xform[drawn]
    axes = x[:, :, :3]  # parallelepiped AABB: base + Σ min/max(0, column)
    lo = (x[:, :, 3] + np.minimum(axes, 0).sum(axis=2)).min(axis=0)
    hi = (x[:, :, 3] + np.maximum(axes, 0).sum(axis=2)).max(axis=0)
    sizes = np.linalg.norm(axes, axis=1).max(axis=1)
    return lo.astype(np.float64), hi.astype(np.float64), float(np.median(sizes)) or 0.1


def preview_scene(scene: SceneIR) -> PreviewScene:
    lo, hi, feature = _bounds(scene)
    return PreviewScene(
        _oriented_boxes(scene),
        _batch(scene, K.SPHERE),
        _batch(scene, K.DOT),
        _batch(scene, K.LINE),
        _batch(scene, K.GRID),
        _triangles(scene),
        lo,
        hi,
        feature,
    )
