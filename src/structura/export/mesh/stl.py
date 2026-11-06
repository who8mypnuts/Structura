"""Binary STL for 3D printing (docs/15 §3): millimetres, optional watertight union (manifold3d), placed on
the build plate."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, TriMesh, tessellate
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register

RECORD = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
UNION_BATCH = 1024


def stl_bytes(triangles: np.ndarray) -> bytes:
    """triangles: float32[T, 3, 3]."""
    r = np.zeros(len(triangles), RECORD)
    r["v"] = triangles
    n = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    r["n"] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    header = b"Structura STL export".ljust(80, b" ")
    return header + np.uint32(len(r)).tobytes() + r.tobytes()


def welded(corners: np.ndarray, quantum: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Merge coincident corners (T,3,3) by quantised position: the shared vertices a manifold needs."""
    flat = corners.reshape(-1, 3).astype(np.float32)
    keys = np.round(flat / quantum).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return flat[first], inverse.reshape(-1, 3).astype(np.uint32)


def watertight(mesh: TriMesh) -> np.ndarray:
    """Union of every instance's closed shell into one manifold (hierarchical, batches of 1,024)."""
    import manifold3d as mf  # noqa: PLC0415 - heavy optional-path import

    solids = []
    for owner in np.unique(mesh.owners):
        points, tris = welded(mesh.positions[mesh.indices[mesh.owners == owner]])
        m = mf.Manifold(mf.Mesh(points, tris))
        if m.status() == mf.Error.NoError and not m.is_empty():
            solids.append(m)
    while len(solids) > 1:
        solids = [mf.Manifold.batch_boolean(solids[i : i + UNION_BATCH], mf.OpType.Add)
                  for i in range(0, len(solids), UNION_BATCH)]  # fmt: skip
    if not solids:
        return np.zeros((0, 3, 3), np.float32)
    out = solids[0].to_mesh()
    return np.asarray(out.vert_properties, np.float32)[:, :3][np.asarray(out.tri_verts)]


class StlExporter(Exporter):
    name = "stl"
    title = "STL (binary, 3D printing)"
    extensions: tuple[str, ...] = (".stl",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 10.0, "Millimetres per unit", range=(1e-6, 1e6)),
        ParamSpec("watertight", ParamType.BOOL, False, "Watertight union (manifold3d)"),
        ParamSpec("on_plate", ParamType.BOOL, True, "Place on the build plate (min z = 0)"),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        mesh = tessellate(job.scene, TessOptions(lod=o["lod"]))
        job.check()
        tris = watertight(mesh) if o["watertight"] else mesh.positions[mesh.indices]
        tris = job.model.points(tris.reshape(-1, 3)).reshape(-1, 3, 3)
        if o["on_plate"] and len(tris):
            tris[:, :, 2] -= tris[:, :, 2].min()
        path.write_bytes(stl_bytes(tris.astype(np.float32)))
        return ExportReport(path, (path,), {"triangles": len(tris)})


register(StlExporter())
