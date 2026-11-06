"""VRML97 (.wrl) for legacy viewers (docs/15 §3, the 1.5 roadmap's "VRML" request): the background and the
script camera (shared with X3D), and either one baked IndexedFaceSet with per-vertex colours, or (instanced,
the default) DEF/USE prototypes placed by exact Transforms plus the baked remainder (placed.py)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.geometry.trimesh import TriMesh
from ...core.geometry.unit_shapes import Mesh
from ...core.params import ParamSpec
from ..base import Exporter, ExportJob, ExportReport, register
from .obj import COMMON
from .placed import PlacedScene, colour_key, first_uses, floats, placed_scene
from .x3d import INSTANCING, viewpoint


def _viewpoint(job: ExportJob) -> str:
    fields = "".join(f"  {k} {v}\n" for k, v in viewpoint(job).items())
    return f'Viewpoint {{\n  description "Structura"\n{fields}}}\n'


def _faces(indices: np.ndarray) -> str:
    closed = np.hstack([indices.astype(np.int64), np.full((len(indices), 1), -1)])
    return " ".join(map(str, closed.ravel().tolist()))


def _face_set(points: np.ndarray, normals: np.ndarray, indices: np.ndarray, colours: np.ndarray | None) -> str:
    colour = f"    color Color {{ color [ {floats(colours[:, :3])} ] }}\n" if colours is not None else ""
    per_vertex = "TRUE" if colours is not None else "FALSE"
    return (
        f"IndexedFaceSet {{\n    solid FALSE colorPerVertex {per_vertex} normalPerVertex TRUE\n"
        f"    coord Coordinate {{ point [ {floats(points)} ] }}\n"
        f"    normal Normal {{ vector [ {floats(normals)} ] }}\n{colour}"
        f"    coordIndex [ {_faces(indices)} ]\n  }}"
    )


def baked_shape(mesh: TriMesh, points: np.ndarray, normals: np.ndarray) -> str:
    geometry = _face_set(points, normals, mesh.indices, mesh.colors)
    appearance = "Appearance { material Material { diffuseColor 1 1 1 } }"
    return f"Shape {{\n  appearance {appearance}\n  geometry {geometry}\n}}\n"


def _placed_shape(key: str, defined: bool, mesh: Mesh) -> str:
    return f"DEF {key} {_face_set(mesh.positions, mesh.normals, mesh.indices, None)}" if defined else f"USE {key}"


def _appearance(key: str, defined: bool, rgba: np.ndarray) -> str:
    if not defined:
        return f"USE {key}"
    return f"DEF {key} Appearance {{ material Material {{ diffuseColor {floats(rgba[:3])} "\
           f"transparency {1 - float(rgba[3]):.6g} }} }}"  # fmt: skip


def instanced_text(placed: PlacedScene) -> str:
    protos = [p.group.proto.key for p in placed.placements]
    colours = [colour_key(p.rgba) for p in placed.placements]
    out = []
    for p, (pk, pdef), (ck, cdef) in zip(placed.placements, first_uses(protos), first_uses(colours), strict=True):
        fields = " ".join(f"{k} {v}" for k, v in p.fields.items())
        geometry = _placed_shape(pk, pdef, p.group.proto.mesh)
        shape = f"Shape {{ appearance {_appearance(ck, cdef, p.rgba)} geometry {geometry} }}"
        out.append(f"Transform {{ {fields} children [ {shape} ] }}\n")
    if placed.rest.triangles:
        out.append(baked_shape(placed.rest, placed.rest_points, placed.rest_normals))
    return "".join(out)


class VrmlExporter(Exporter):
    name = "vrml"
    title = "VRML97 (.wrl)"
    extensions: tuple[str, ...] = (".wrl",)
    params: tuple[ParamSpec, ...] = (*COMMON, INSTANCING)

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        sky = floats(np.asarray(job.model.background))
        head = f"#VRML V2.0 utf8\n# Structura export\nBackground {{ skyColor [ {sky} ] }}\n{_viewpoint(job)}"
        if job.options["instancing"]:
            placed = placed_scene(job, job.options["lod"])
            path.write_text(head + instanced_text(placed), encoding="utf-8")
            return ExportReport(
                path, (path,), {"instances": len(placed.placements), "triangles": placed.rest.triangles}
            )
        mesh = tessellate(job.scene, TessOptions(lod=job.options["lod"]))
        job.check()
        points, normals = job.model.points(mesh.positions), job.model.directions(mesh.normals)
        path.write_text(head + baked_shape(mesh, points, normals), encoding="utf-8")
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles})


register(VrmlExporter())
