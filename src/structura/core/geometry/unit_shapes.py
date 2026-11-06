"""Triangle meshes of the unit primitives in Structure Synth's conventions (docs/05 §9.6, docs/15).

Every shape lives in the unit cube [0,1]³ of its instance frame. Meshes are (positions float32[V,3],
normals float32[V,3], indices uint32[T,3]) with outward normals and counter-clockwise front faces.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np


@dataclass(frozen=True)
class Mesh:
    positions: np.ndarray
    normals: np.ndarray
    indices: np.ndarray

    @property
    def triangles(self) -> int:
        return int(self.indices.shape[0])

    def interleaved(self) -> np.ndarray:
        """float32[V, 6]: position, normal."""
        return np.hstack([self.positions, self.normals]).astype(np.float32)


def _frozen(mesh: Mesh) -> Mesh:
    """Orient every triangle counter-clockwise around its vertex normals, then make the arrays read-only."""
    p, t = mesh.positions, mesh.indices.copy()
    face = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
    flip = (face * mesh.normals[t].sum(axis=1)).sum(axis=1) < 0
    t[flip] = t[flip][:, ::-1]
    mesh = Mesh(mesh.positions, mesh.normals, t)
    for a in (mesh.positions, mesh.normals, mesh.indices):
        a.flags.writeable = False
    return mesh


@cache
def unit_box() -> Mesh:
    """24 vertices (flat normals per face), 12 triangles."""
    positions: list[np.ndarray] = []
    normals: list[np.ndarray] = []
    indices: list[tuple[int, int, int]] = []
    for axis in range(3):
        for side in (0.0, 1.0):
            n = np.zeros(3)
            n[axis] = 1.0 if side else -1.0
            u, v = (axis + 1) % 3, (axis + 2) % 3
            base = len(positions)
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = np.zeros(3)
                p[axis], p[u], p[v] = side, a, b
                positions.append(p)
                normals.append(n)
            quad = [(0, 1, 2), (0, 2, 3)] if side else [(0, 2, 1), (0, 3, 2)]
            indices += [(base + i, base + j, base + k) for i, j, k in quad]
    return _frozen(Mesh(np.array(positions, np.float32), np.array(normals, np.float32), np.array(indices, np.uint32)))


@cache
def unit_sphere(rings: int = 16, segments: int = 32) -> Mesh:
    """UV sphere inscribed in the unit cube (centre 0.5, radius 0.5)."""
    theta = np.linspace(0, np.pi, rings + 1)
    phi = np.linspace(0, 2 * np.pi, segments + 1)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    n = np.stack([np.sin(t) * np.cos(p), np.cos(t), np.sin(t) * np.sin(p)], -1).reshape(-1, 3)
    row = segments + 1
    quads = [
        (r * row + s, (r + 1) * row + s, (r + 1) * row + s + 1, r * row + s + 1)
        for r in range(rings)
        for s in range(segments)
    ]
    tris = [tri for a, b, c, d in quads for tri in ((a, c, b), (a, d, c))]
    return _frozen(Mesh((0.5 + 0.5 * n).astype(np.float32), n.astype(np.float32), np.array(tris, np.uint32)))


@cache
def unit_cylinder(segments: int = 32, top_scale: float = 1.0) -> Mesh:
    """Capped cylinder (or cone when top_scale = 0) along x from (0,.5,.5) to (1,.5,.5), radius 0.5."""
    ang = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    ring = np.stack([np.cos(ang), np.sin(ang)], -1) * 0.5
    slope = 0.5 * (1.0 - top_scale)  # radial drop over the unit length, for cone normals
    positions: list[tuple[float, float, float]] = []
    normals: list[object] = []
    indices: list[tuple[int, int, int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        base = len(positions)
        for x, k, scale in ((0.0, i, 1.0), (0.0, j, 1.0), (1.0, j, top_scale), (1.0, i, top_scale)):
            y, z = ring[k] * scale
            positions.append((x, 0.5 + y, 0.5 + z))
            nr = ring[k] / 0.5
            nn = np.array([slope, nr[0], nr[1]])
            normals.append(nn / np.linalg.norm(nn))
        indices += [(base, base + 2, base + 1), (base, base + 3, base + 2)]
    for x, scale, sign in ((0.0, 1.0, -1.0), (1.0, top_scale, 1.0)):
        if scale <= 0:
            continue
        centre = len(positions)
        positions.append((x, 0.5, 0.5))
        normals.append((sign, 0.0, 0.0))
        for k in range(segments):
            y, z = ring[k] * scale
            positions.append((x, 0.5 + y, 0.5 + z))
            normals.append((sign, 0.0, 0.0))
        for k in range(segments):
            a, b = centre + 1 + k, centre + 1 + (k + 1) % segments
            indices.append((centre, b, a) if sign < 0 else (centre, a, b))
    return _frozen(Mesh(np.array(positions, np.float32), np.array(normals, np.float32), np.array(indices, np.uint32)))
