"""X3D (ISO/IEC 19775, XML encoding) for web viewers (X_ITE, X3DOM) and CAD tools (docs/15 §3): the background
colour, the script camera, and either one baked IndexedTriangleSet with per-vertex colours, or (instanced, the
default) DEF/USE prototypes placed by exact Transforms plus the baked remainder (placed.py)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ...core.geometry.affine import quaternions
from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.geometry.trimesh import TriMesh
from ...core.geometry.unit_shapes import Mesh
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register
from .obj import COMMON
from .placed import PlacedScene, colour_key, first_uses, floats, placed_scene

INSTANCING = ParamSpec("instancing", ParamType.BOOL, True, "Instanced prototypes (DEF/USE)")

HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">\n'
    '<X3D profile="Interchange" version="4.0"><head><meta name="generator" content="Structura"/></head><Scene>'
)


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


def _geometry(key: str, defined: bool, proto_mesh: Mesh) -> str:
    if not defined:
        return f'<IndexedTriangleSet USE="{key}"/>'
    index = " ".join(map(str, proto_mesh.indices.ravel().tolist()))
    return (f'<IndexedTriangleSet DEF="{key}" solid="false" normalPerVertex="true" index="{index}">'
            f'<Coordinate point="{floats(proto_mesh.positions)}"/><Normal vector="{floats(proto_mesh.normals)}"/>'
            "</IndexedTriangleSet>")  # fmt: skip


def _appearance(key: str, defined: bool, rgba: np.ndarray) -> str:
    if not defined:
        return f'<Appearance USE="{key}"/>'
    transparency = f' transparency="{1 - float(rgba[3]):.6g}"' if rgba[3] < 1 else ""
    return f'<Appearance DEF="{key}"><Material diffuseColor="{floats(rgba[:3])}"{transparency}/></Appearance>'


def instanced_xml(placed: PlacedScene) -> str:
    protos = [p.group.proto.key for p in placed.placements]
    colours = [colour_key(p.rgba) for p in placed.placements]
    out = []
    for p, (pk, pdef), (ck, cdef) in zip(placed.placements, first_uses(protos), first_uses(colours), strict=True):
        fields = " ".join(f'{k}="{v}"' for k, v in p.fields.items())
        geometry = _geometry(pk, pdef, p.group.proto.mesh)
        out.append(f"<Transform {fields}><Shape>{_appearance(ck, cdef, p.rgba)}{geometry}</Shape></Transform>")
    if placed.rest.triangles:
        out.append(shape_xml(placed.rest, placed.rest_points, placed.rest_normals))
    return "".join(out)


class X3dExporter(Exporter):
    name = "x3d"
    title = "X3D (XML)"
    extensions: tuple[str, ...] = (".x3d",)
    params: tuple[ParamSpec, ...] = (*COMMON, INSTANCING)

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        background = f'<Background skyColor="{floats(np.asarray(job.model.background))}"/>'
        head = HEADER + background + viewpoint_xml(job)
        if job.options["instancing"]:
            placed = placed_scene(job, job.options["lod"])
            path.write_text(head + instanced_xml(placed) + "</Scene></X3D>\n", encoding="utf-8")
            counts = {"instances": len(placed.placements), "triangles": placed.rest.triangles}
            return ExportReport(path, (path,), counts)
        mesh = tessellate(job.scene, TessOptions(lod=job.options["lod"]))
        job.check()
        points, normals = job.model.points(mesh.positions), job.model.directions(mesh.normals)
        path.write_text(head + shape_xml(mesh, points, normals) + "</Scene></X3D>\n", encoding="utf-8")
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles})


register(X3dExporter())
