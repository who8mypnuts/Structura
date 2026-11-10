"""Binary STL for 3D printing (docs/15 §3): millimetres, optional watertight union (manifold3d), placed on
the build plate."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.geometry.trimesh import TriMesh
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register
from ..csg import CSG_OPTION, export_mesh
from ..solids import instance_solids, triangles, union
from .meshlab import MESHLAB_OPTIONS

RECORD = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def stl_bytes(triangles: np.ndarray) -> bytes:
    """triangles: float32[T, 3, 3]."""
    r = np.zeros(len(triangles), RECORD)
    r["v"] = triangles
    n = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    r["n"] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    header = b"Structura STL export".ljust(80, b" ")
    return header + np.uint32(len(r)).tobytes() + r.tobytes()


def watertight(mesh: TriMesh) -> np.ndarray:
    """Union of every instance's closed shell into one manifold (hierarchical, batches of 1,024)."""
    corners, _ = triangles(union(list(instance_solids(mesh).values())))
    return corners


class StlExporter(Exporter):
    name = "stl"
    title = "STL (binary, 3D printing)"
    extensions: tuple[str, ...] = (".stl",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 10.0, "Millimetres per unit", range=(1e-6, 1e6)),
        ParamSpec("watertight", ParamType.BOOL, False, "Watertight union (manifold3d)"),
        ParamSpec("on_plate", ParamType.BOOL, True, "Place on the build plate (min z = 0)"),
        CSG_OPTION,
        *MESHLAB_OPTIONS,
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        mesh, warnings = export_mesh(job)
        job.check()
        tris = watertight(mesh) if o["watertight"] else mesh.positions[mesh.indices]
        tris = job.model.points(tris.reshape(-1, 3)).reshape(-1, 3, 3)
        if o["on_plate"] and len(tris):
            tris[:, :, 2] -= tris[:, :, 2].min()
        path.write_bytes(stl_bytes(tris.astype(np.float32)))
        return ExportReport(path, (path,), {"triangles": len(tris)}, warnings)


register(StlExporter())
