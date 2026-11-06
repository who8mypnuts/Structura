"""USD export (usd-core, docs/15 §4.1).

*instanced* (default): PointInstancers for TRS boxes and spheres (per material); lines as BasisCurves, dots as
Points; the rest — grids, meshes, triangles, v2 solids and sheared boxes — baked into meshes per material,
or, with the *matrix* shear policy, placed by `xformOp:transform` on instanceable references of unit
prototypes (exact, no tessellation per instance). *flattened*: one mesh per material with vertex colours.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pxr import UsdGeom, UsdUtils, Vt

from ...core.geometry.tessellate import TessOptions, iter_tessellate
from ...core.geometry.trimesh import TriMesh
from ...core.geometry.unit_shapes import unit_box
from ...core.geometry.v2_shapes import V2_KINDS
from ...core.params import ParamSpec, ParamType
from ...core.scene.ir import PrimitiveKind as K
from ...core.scene.ir import SceneIR
from ..base import Exporter, ExportJob, ExportReport, register
from .instancing import InstanceGroup, instance_groups
from .usd_matrix import matrix_instances
from .usd_stage import ROOT, bind, camera, display_colors, material, new_stage

SUFFIXES = (".usd", ".usda", ".usdc", ".usdz")


def _vec3(a: np.ndarray) -> Vt.Vec3fArray:
    return Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(a, np.float32))


def _mesh(stage: object, path: str, mesh: TriMesh, job: ExportJob) -> UsdGeom.Mesh:
    prim = UsdGeom.Mesh.Define(stage, path)
    prim.CreatePointsAttr(_vec3(job.model.points(mesh.positions)))
    prim.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(mesh.triangles, 3, np.int32)))
    prim.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(mesh.indices.astype(np.int32).ravel()))
    prim.CreateNormalsAttr(_vec3(job.model.directions(mesh.normals)))
    prim.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    prim.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    display_colors(prim, mesh.colors, UsdGeom.Tokens.vertex)
    return prim


def _box_prototype(stage: object, path: str) -> None:
    box = unit_box()
    proto = UsdGeom.Mesh.Define(stage, path)
    proto.CreatePointsAttr(_vec3(box.positions))
    proto.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(box.triangles, 3, np.int32)))
    proto.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(box.indices.astype(np.int32).ravel()))
    proto.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)


def _instancer(stage: object, path: str, group: InstanceGroup, scene: SceneIR) -> UsdGeom.PointInstancer:
    inst = UsdGeom.PointInstancer.Define(stage, path)
    proto_path = f"{path}/Prototypes/{'Box' if group.kind == K.BOX else 'Sphere'}"
    if group.kind == K.BOX:
        _box_prototype(stage, proto_path)
    else:
        UsdGeom.Sphere.Define(stage, proto_path).CreateRadiusAttr(1.0)
    inst.CreatePrototypesRel().AddTarget(proto_path)
    inst.CreateProtoIndicesAttr(Vt.IntArray.FromNumpy(np.zeros(len(group.rows), np.int32)))
    inst.CreatePositionsAttr(_vec3(group.translation))
    inst.CreateScalesAttr(_vec3(group.scale))
    quats = np.ascontiguousarray(group.rotation[:, [3, 0, 1, 2]], np.float16)  # (w, x, y, z)
    inst.CreateOrientationsAttr(Vt.QuathArray.FromNumpy(quats))
    display_colors(inst, scene.rgba[group.rows], UsdGeom.Tokens.vertex)
    return inst


class UsdExporter(Exporter):
    name = "usd"
    title = "USD (instanced)"
    extensions: tuple[str, ...] = SUFFIXES
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail for baked parts", choices=("low", "medium", "high")),
        ParamSpec("up", ParamType.ENUM, "y", "Up axis", choices=("y", "z")),
        ParamSpec("unit_scale", ParamType.FLOAT, 1.0, "Unit scale", range=(1e-6, 1e6)),
        ParamSpec("line_width", ParamType.FLOAT, 0.02, "Line width (world units)", range=(0.0, 1e6)),
        ParamSpec("mode", ParamType.ENUM, "instanced", "Layout", choices=("instanced", "flattened")),
        ParamSpec("shear", ParamType.ENUM, "bake", "Sheared and v2 solids", choices=("bake", "matrix")),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        usdz = path.suffix.lower() == ".usdz"
        target = path.with_suffix(".usdc") if usdz else path
        stage = new_stage(str(target), job.model)
        counts = self._author(stage, job)
        camera(stage, job.model)
        stage.GetRootLayer().Save()
        if usdz:
            UsdUtils.CreateNewUsdzPackage(str(target), str(path))
            target.unlink()
        return ExportReport(path, (path,), counts)

    def _author(self, stage: object, job: ExportJob) -> dict[str, int]:
        scene, table = job.scene, job.model.materials
        looks = [material(stage, m, i) for i, m in enumerate(table.materials)]
        mat_of_row = table.by_tag[scene.tag] if len(scene) else np.zeros(0, np.int32)
        if job.options["mode"] == "flattened":
            every = np.ones(len(scene), bool)
            self._baked(stage, job, every, looks, mat_of_row)
            return {"instanced": 0, "baked_rows": len(scene)}
        groups, sheared = instance_groups(job)
        for group in groups:
            inst = _instancer(stage, f"{ROOT}/{group.kind.name.title()}s_{group.material}", group, scene)
            bind(inst.GetPrim(), looks[group.material])
        self._curves_points(stage, job)
        rest = sheared | np.isin(scene.kind, (K.GRID, K.MESH, K.TRIANGLE, *V2_KINDS))
        placed = np.zeros(len(scene), bool)
        if job.options["shear"] == "matrix":
            placed = matrix_instances(stage, job, rest, looks, mat_of_row)
        self._baked(stage, job, rest & ~placed, looks, mat_of_row)
        return {"instanced": sum(len(g.rows) for g in groups), "baked_rows": int((rest & ~placed).sum()),
                "matrix_instances": int(placed.sum())}  # fmt: skip

    def _curves_points(self, stage: object, job: ExportJob) -> None:
        scene = job.scene
        lines = np.nonzero(scene.kind == K.LINE)[0]
        if len(lines):
            x = scene.xform[lines]
            a = x[:, :, 3] + 0.5 * (x[:, :, 1] + x[:, :, 2])
            pts = job.model.points(np.stack([a, a + x[:, :, 0]], axis=1).reshape(-1, 3))
            curves = UsdGeom.BasisCurves.Define(stage, f"{ROOT}/Lines")
            curves.CreateTypeAttr(UsdGeom.Tokens.linear)
            curves.CreatePointsAttr(_vec3(pts))
            curves.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(lines), 2, np.int32)))
            curves.CreateWidthsAttr(Vt.FloatArray.FromNumpy(np.full(1, job.options["line_width"], np.float32)))
            curves.SetWidthsInterpolation(UsdGeom.Tokens.constant)
            display_colors(curves, scene.rgba[lines], UsdGeom.Tokens.uniform)
        dots = np.nonzero(scene.kind == K.DOT)[0]
        if len(dots):
            x = scene.xform[dots]
            points = UsdGeom.Points.Define(stage, f"{ROOT}/Dots")
            points.CreatePointsAttr(_vec3(job.model.points(x[:, :, 3] + 0.5 * x[:, :, :3].sum(axis=2))))
            display_colors(points, scene.rgba[dots], UsdGeom.Tokens.vertex)

    def _baked(self, stage: object, job: ExportJob, baked: np.ndarray, looks: list, mat_of_row: np.ndarray) -> None:  # type: ignore[type-arg]
        scene = job.scene
        keep = baked & (scene.kind != K.TEMPLATE)
        if not keep.any():
            return
        sub = scene.subset(np.nonzero(keep)[0])
        mesh = TriMesh.concat(list(iter_tessellate(sub, TessOptions(lod=job.options["lod"]))))
        owners_mat = mat_of_row[np.nonzero(keep)[0]][mesh.owners]
        for m in np.unique(owners_mat):
            mask = owners_mat == m
            tri = mesh.indices[mask]
            used, remap = np.unique(tri, return_inverse=True)
            part = TriMesh(mesh.positions[used], mesh.normals[used], mesh.colors[used],
                           remap.reshape(-1, 3).astype(np.uint32), mesh.owners[mask])  # fmt: skip
            bind(_mesh(stage, f"{ROOT}/Baked_{m}", part, job).GetPrim(), looks[int(m)])


register(UsdExporter())
