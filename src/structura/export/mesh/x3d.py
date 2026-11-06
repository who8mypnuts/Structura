"""X3D (ISO/IEC 19775, XML encoding) for web viewers (X_ITE, X3DOM) and CAD tools (docs/15 §4, M8): one
IndexedTriangleSet with per-vertex colours and normals, the background colour and the script camera."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ...core.geometry.affine import quaternions
from ...core.geometry.tessellate import TessOptions, TriMesh, tessellate
from ...core.params import ParamSpec
from ..base import Exporter, ExportJob, ExportReport, register
from .obj import COMMON

HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">\n'
    '<X3D profile="Interchange" version="4.0"><head><meta name="generator" content="Structura"/></head><Scene>'
)


def floats(a: np.ndarray) -> str:
    return " ".join(f"{v:.6g}" for v in np.asarray(a, np.float64).ravel().tolist())


def shape_xml(mesh: TriMesh, points: np.ndarray, normals: np.ndarray) -> str:
    index = " ".join(map(str, mesh.indices.ravel().tolist()))
    return (
        '<Shape><Appearance><Material diffuseColor="1 1 1"/></Appearance>'
        f'<IndexedTriangleSet solid="false" normalPerVertex="true" colorPerVertex="true" index="{index}">'
        f'<Coordinate point="{floats(points)}"/><Normal vector="{floats(normals)}"/>'
        f'<ColorRGBA color="{floats(mesh.colors)}"/></IndexedTriangleSet></Shape>'
    )


def viewpoint(job: ExportJob) -> dict[str, str]:
    """The script camera as Viewpoint fields (shared by X3D and VRML97). Viewpoints look down -Z with +Y up,
    so the orientation is the rotation whose columns are (right, up, -forward), written as axis-angle."""
    cam = job.model.camera
    forward, right, up = (job.model.directions(v[None].astype(np.float32))[0] for v in cam.basis)
    m = np.stack([right, up, -forward], axis=1)
    m /= np.linalg.norm(m, axis=0, keepdims=True)
    x, y, z, w = quaternions(m[None])[0].tolist()
    angle = 2 * math.atan2(math.sqrt(x * x + y * y + z * z), w)
    axis = np.array([x, y, z]) if angle > 1e-9 else np.array([0.0, 0.0, 1.0])
    axis /= np.linalg.norm(axis)
    eye = job.model.points(np.asarray(cam.eye, np.float32)[None])[0]
    half = math.tan(math.radians(cam.fov_y_deg) / 2)
    fov = 2 * math.atan(half * min(1.0, job.model.aspect))  # X3D: the field of view of the smaller side
    return {"position": floats(eye), "orientation": f"{floats(axis)} {angle:.6g}", "fieldOfView": f"{fov:.6g}"}


def viewpoint_xml(job: ExportJob) -> str:
    fields = " ".join(f'{k}="{v}"' for k, v in viewpoint(job).items())
    return f'<Viewpoint description="Structura" {fields}/>'


class X3dExporter(Exporter):
    name = "x3d"
    title = "X3D (XML)"
    extensions: tuple[str, ...] = (".x3d",)
    params: tuple[ParamSpec, ...] = COMMON

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        mesh = tessellate(job.scene, TessOptions(lod=job.options["lod"]))
        job.check()
        points, normals = job.model.points(mesh.positions), job.model.directions(mesh.normals)
        background = f'<Background skyColor="{floats(np.asarray(job.model.background))}"/>'
        body = background + viewpoint_xml(job) + shape_xml(mesh, points, normals)
        path.write_text(HEADER + body + "</Scene></X3D>\n", encoding="utf-8")
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles})


register(X3dExporter())
