"""Exact CPU picking (docs/08 §6, §9): the nearest instance hit by a camera ray, and the hit distance.

Every instance is tested as its oriented unit cube [0,1]³ (the frame every primitive lives in): the ray is
taken into each instance's frame and slab-tested, in chunks so memory stays bounded. Used by the compute
preview (which has no id buffer) and for Alt+click focusing in both viewports.
"""

from __future__ import annotations

import numpy as np

from ..core.scene.camera import Camera
from ..core.scene.ir import PrimitiveKind, SceneIR
from .camera import camera_matrices

CHUNK = 262_144


def camera_ray(camera: Camera, size: tuple[int, int], x: float, y: float) -> tuple[np.ndarray, np.ndarray]:
    """(origin, unit direction) of the ray through widget pixel (x, y), y from the top."""
    w, h = max(1, size[0]), max(1, size[1])
    m = camera_matrices(camera, w / h, np.full(3, -1.0), np.full(3, 1.0))
    inverse = np.linalg.inv(m.proj @ m.view)
    ndc = np.array([2 * (x + 0.5) / w - 1, 1 - 2 * (y + 0.5) / h])
    near, far = (inverse @ np.array([ndc[0], ndc[1], z, 1.0]) for z in (-1.0, 1.0))
    a, b = near[:3] / near[3], far[:3] / far[3]
    direction = (b - a) / np.linalg.norm(b - a)
    return a, direction


def _chunk_hits(xform: np.ndarray, origin: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """Entry distance along the ray for each instance's unit cube (inf where missed)."""
    linear, base = xform[:, :, :3].astype(np.float64), xform[:, :, 3].astype(np.float64)
    det = np.linalg.det(linear)
    ok = np.abs(det) > 1e-20
    inverse = np.zeros_like(linear)
    inverse[ok] = np.linalg.inv(linear[ok])
    o = np.einsum("nij,nj->ni", inverse, origin - base)
    d = np.einsum("nij,j->ni", inverse, direction)
    with np.errstate(divide="ignore", invalid="ignore"):
        t0, t1 = (0.0 - o) / d, (1.0 - o) / d
    near = np.nanmax(np.minimum(t0, t1), axis=1)
    far = np.nanmin(np.maximum(t0, t1), axis=1)
    hit = ok & (far >= np.maximum(near, 0.0))
    return np.where(hit, np.maximum(near, 0.0), np.inf)


def pick(scene: SceneIR, origin: np.ndarray, direction: np.ndarray) -> tuple[int, float] | None:
    """(SceneIR row, distance) of the nearest instance on the ray, or None."""
    best: tuple[int, float] | None = None
    drawn = np.flatnonzero(scene.kind != PrimitiveKind.TEMPLATE)
    for start in range(0, len(drawn), CHUNK):
        rows = drawn[start : start + CHUNK]
        t = _chunk_hits(scene.xform[rows], origin, direction)
        index = int(np.argmin(t))
        if np.isfinite(t[index]) and (best is None or t[index] < best[1]):
            best = (int(rows[index]), float(t[index]))
    return best
