"""VRML97 (.wrl) for legacy viewers (docs/15 §3, the 1.5 roadmap's "VRML" request): one IndexedFaceSet with
per-vertex colours and normals, the background and the script camera (shared with X3D)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.params import ParamSpec
from ..base import Exporter, ExportJob, ExportReport, register
from .obj import COMMON
from .x3d import floats, viewpoint


def _viewpoint(job: ExportJob) -> str:
    fields = "".join(f"  {k} {v}\n" for k, v in viewpoint(job).items())
    return f'Viewpoint {{\n  description "Structura"\n{fields}}}\n'


def _faces(indices: np.ndarray) -> str:
    closed = np.hstack([indices.astype(np.int64), np.full((len(indices), 1), -1)])
    return " ".join(map(str, closed.ravel().tolist()))


class VrmlExporter(Exporter):
    name = "vrml"
    title = "VRML97 (.wrl)"
    extensions: tuple[str, ...] = (".wrl",)
    params: tuple[ParamSpec, ...] = COMMON

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        mesh = tessellate(job.scene, TessOptions(lod=job.options["lod"]))
        job.check()
        points, normals = job.model.points(mesh.positions), job.model.directions(mesh.normals)
        text = (
            "#VRML V2.0 utf8\n# Structura export\n"
            f"Background {{ skyColor [ {floats(np.asarray(job.model.background))} ] }}\n{_viewpoint(job)}"
            "Shape {\n  appearance Appearance { material Material { diffuseColor 1 1 1 } }\n"
            "  geometry IndexedFaceSet {\n    solid FALSE colorPerVertex TRUE normalPerVertex TRUE\n"
            f"    coord Coordinate {{ point [ {floats(points)} ] }}\n"
            f"    normal Normal {{ vector [ {floats(normals)} ] }}\n"
            f"    color Color {{ color [ {floats(mesh.colors[:, :3])} ] }}\n"
            f"    coordIndex [ {_faces(mesh.indices)} ]\n  }}\n}}\n"
        )
        path.write_text(text, encoding="utf-8")
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles})


register(VrmlExporter())
