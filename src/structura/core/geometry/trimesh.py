"""Triangle meshes and their placement per instance (shared by tessellation, export and the preview).

World vertices for a chunk of instances come from one einsum; normals use the cofactor of each linear part;
winding flips automatically for mirrored instances (det < 0), which fixes 1.5's face-culling bug.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .unit_shapes import Mesh


@dataclass(frozen=True)
class TriMesh:
    """Triangles with per-vertex normals and colours, and the scene row each triangle came from.

    Attributes:
        positions: float32[V, 3] vertex positions.
        normals: float32[V, 3] vertex normals.
        colors: float32[V, 4] sRGB colour and alpha (the authored colour).
        indices: uint32[T, 3] vertex indices of each triangle.
        owners: int64[T] the SceneIR row of each triangle.
    """

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

    def select(self, faces: np.ndarray) -> TriMesh:
        """Keeps some triangles.

        Args:
            faces: A boolean mask over the triangles.

        Returns:
            A mesh of the selected triangles with only the vertices they use.
        """
        tris = self.indices[faces]
        used, remap = np.unique(tris, return_inverse=True)
        return TriMesh(self.positions[used], self.normals[used], self.colors[used],
                       remap.reshape(-1, 3).astype(np.uint32), self.owners[faces])  # fmt: skip

    @classmethod
    def concat(cls, parts: list[TriMesh]) -> TriMesh:
        parts = [p for p in parts if p.triangles]
        if not parts:
            return cls.empty()
        if len(parts) == 1:
            return parts[0]
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


def normalise(v: np.ndarray) -> np.ndarray:
    n = np.sqrt((v * v).sum(axis=-1, keepdims=True))
    out: np.ndarray = np.where(n > 1e-30, v / np.maximum(n, 1e-30), np.array([0, 0, 1], np.float32))
    return out.astype(np.float32)


def _apply(linear: np.ndarray, points: np.ndarray) -> np.ndarray:
    """(N,3,3) · (V,3) → (N,V,3): a batched matrix product (much faster than einsum for tiny matrices)."""
    out: np.ndarray = np.matmul(linear, points.T.astype(linear.dtype)).transpose(0, 2, 1)
    return out


def instanced(mesh: Mesh, linear: np.ndarray, offset: np.ndarray, colors: np.ndarray, rows: np.ndarray) -> TriMesh:
    """Place ``mesh`` with per-instance affine (linear (N,3,3), offset (N,3)); one colour per instance."""
    n, v = len(rows), len(mesh.positions)
    if n == 0:
        return TriMesh.empty()
    pos = _apply(linear, mesh.positions) + offset[:, None, :]
    nrm = normalise(_apply(cofactor(linear), mesh.normals))
    flip = np.linalg.det(linear) < 0
    tri = np.broadcast_to(mesh.indices, (n, *mesh.indices.shape)).copy()
    tri[flip] = tri[flip][:, :, ::-1]
    tri = tri + (np.arange(n, dtype=np.uint32) * np.uint32(v))[:, None, None]
    cols = np.repeat(colors.astype(np.float32), v, axis=0)
    owners = np.repeat(rows.astype(np.int64), mesh.triangles)
    return TriMesh(pos.reshape(-1, 3).astype(np.float32), nrm.reshape(-1, 3), cols, tri.reshape(-1, 3), owners)


def beams(a: np.ndarray, b: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Affines mapping the unit cube onto square beams from a to b (N,3) with half-width radius (N,)."""
    axis = b - a
    length = np.linalg.norm(axis, axis=1, keepdims=True)
    d = axis / np.maximum(length, 1e-30)
    helper = np.where(np.abs(d[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    u = normalise(np.cross(d, helper))
    w = np.cross(d, u)
    r = radius[:, None]
    linear = np.stack([axis, 2 * r * u, 2 * r * w], axis=2).astype(np.float32)
    return linear, (a - r * u - r * w).astype(np.float32)
