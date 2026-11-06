"""Closed solids for 3D printing (docs/15 §3.1), with manifold3d: per-instance manifolds (carrying their
colour as vertex properties, so booleans keep it), hierarchical unions, and back to triangles."""

from __future__ import annotations

import manifold3d as mf
import numpy as np

from ..core.geometry.trimesh import TriMesh

UNION_BATCH = 1024
COLOUR = slice(3, 7)  # vertex property columns after x, y, z


def welded(corners: np.ndarray, quantum: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Merge coincident corners (T,3,3) by quantised position: the shared vertices a manifold needs."""
    flat = corners.reshape(-1, 3).astype(np.float32)
    keys = np.round(flat / quantum).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return flat[first], inverse.reshape(-1, 3).astype(np.uint32)


def instance_solids(mesh: TriMesh) -> dict[int, mf.Manifold]:
    """One manifold per SceneIR row whose shell is closed (open shells, e.g. single triangles, are skipped)."""
    solids = {}
    for owner in np.unique(mesh.owners).tolist():
        tris = mesh.indices[mesh.owners == owner]
        points, faces = welded(mesh.positions[tris])
        colour = np.broadcast_to(mesh.colors[tris[0, 0]], (len(points), 4))
        m = mf.Manifold(mf.Mesh(np.ascontiguousarray(np.hstack([points, colour]), np.float32), faces))
        if m.status() == mf.Error.NoError and not m.is_empty():
            solids[owner] = m
    return solids


def union(solids: list[mf.Manifold]) -> mf.Manifold:
    """Hierarchical union in batches of 1,024."""
    while len(solids) > 1:
        solids = [mf.Manifold.batch_boolean(solids[i : i + UNION_BATCH], mf.OpType.Add)
                  for i in range(0, len(solids), UNION_BATCH)]  # fmt: skip
    return solids[0] if solids else mf.Manifold()


def triangles(solid: mf.Manifold) -> tuple[np.ndarray, np.ndarray]:
    """(float32[T,3,3] corners, float32[T,4] colour of each triangle)."""
    out = solid.to_mesh()
    props = np.asarray(out.vert_properties, np.float32)
    faces = np.asarray(out.tri_verts, np.int64)
    if not len(faces):
        return np.zeros((0, 3, 3), np.float32), np.zeros((0, 4), np.float32)
    colours = props[faces[:, 0], COLOUR] if props.shape[1] >= 7 else np.ones((len(faces), 4), np.float32)
    return props[:, :3][faces], colours


def as_trimesh(corners: np.ndarray, colours: np.ndarray) -> TriMesh:
    """A flat-shaded TriMesh (owners 0) from triangle corners."""
    n = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    count = len(corners)
    indices = np.arange(3 * count, dtype=np.uint32).reshape(-1, 3)
    points, normals = corners.reshape(-1, 3).astype(np.float32), np.repeat(n, 3, axis=0).astype(np.float32)
    return TriMesh(
        points, normals, np.repeat(colours, 3, axis=0).astype(np.float32), indices, np.zeros(count, np.int64)
    )
