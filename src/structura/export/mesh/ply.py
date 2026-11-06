"""Binary little-endian PLY with per-vertex normals and RGBA colours (docs/15 §3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.geometry.trimesh import TriMesh
from ...core.params import ParamSpec
from ..base import Exporter, ExportJob, ExportReport, register
from ..csg import CSG_OPTION, export_mesh
from .obj import COMMON

VERTEX = np.dtype([("p", "<f4", 3), ("n", "<f4", 3), ("c", "u1", 4)])
FACE = np.dtype([("count", "u1"), ("v", "<i4", 3)])


def ply_header(vertices: int, faces: int) -> bytes:
    lines = [
        "ply",
        "format binary_little_endian 1.0",
        "comment Structura export",
        f"element vertex {vertices}",
        *(f"property float {p}" for p in ("x", "y", "z", "nx", "ny", "nz")),
        *(f"property uchar {p}" for p in ("red", "green", "blue", "alpha")),
        f"element face {faces}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def ply_bytes(mesh: TriMesh, points: np.ndarray, normals: np.ndarray) -> bytes:
    v = np.empty(len(points), VERTEX)
    v["p"], v["n"] = points, normals
    v["c"] = np.clip(np.rint(mesh.colors * 255), 0, 255).astype(np.uint8)
    f = np.empty(mesh.triangles, FACE)
    f["count"], f["v"] = 3, mesh.indices.astype(np.int32)
    return ply_header(len(v), len(f)) + v.tobytes() + f.tobytes()


class PlyExporter(Exporter):
    name = "ply"
    title = "PLY (binary)"
    extensions: tuple[str, ...] = (".ply",)
    params: tuple[ParamSpec, ...] = (*COMMON, CSG_OPTION)

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        mesh, warnings = export_mesh(job)
        job.check()
        path.write_bytes(ply_bytes(mesh, job.model.points(mesh.positions), job.model.directions(mesh.normals)))
        counts = {"vertices": len(mesh.positions), "triangles": mesh.triangles}
        return ExportReport(path, (path,), counts, warnings)


register(PlyExporter())
