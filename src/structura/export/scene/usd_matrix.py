"""USD 'matrix' shear policy (docs/15 §2.2, §4.1): instances a PointInstancer cannot hold (sheared boxes, the
v2 solids) become Xform prims with one `xformOp:transform`, each an instanceable reference to a unit
prototype, so they stay exact and light. Colour is a constant displayColor primvar on the instance prim
(inherited by the prototype's mesh); the material is bound on the instance prim."""

from __future__ import annotations

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from ..affine_instances import affine_groups
from ..base import ExportJob
from .usd_stage import ROOT, bind

PROTOTYPES = "/StructuraPrototypes"


def _name(key: str) -> str:
    return key.replace("-", "_").replace(".", "_")


def _prototype(stage: Usd.Stage, key: str, positions: np.ndarray, normals: np.ndarray, tris: np.ndarray) -> str:
    path = f"{PROTOTYPES}/{_name(key)}"
    if not stage.GetPrimAtPath(path):
        stage.CreateClassPrim(path)
        mesh = UsdGeom.Mesh.Define(stage, f"{path}/Mesh")
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(positions, np.float32)))
        mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(normals, np.float32)))
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(tris), 3, np.int32)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(tris.astype(np.int32).ravel()))
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    return path


def usd_matrix(affine: np.ndarray) -> Gf.Matrix4d:
    """Column-vector [L | t] → USD's row-vector 4×4 (translation in the last row)."""
    m = np.eye(4)
    m[:3, :3], m[3, :3] = affine[:, :3].T, affine[:, 3]
    return Gf.Matrix4d(*m.ravel().tolist())


def _place(stage: Usd.Stage, path: str, proto: str, affine: np.ndarray, rgba: np.ndarray) -> Usd.Prim:
    xf = UsdGeom.Xform.Define(stage, path)
    xf.AddTransformOp().Set(usd_matrix(affine))
    prim = xf.GetPrim()
    prim.GetReferences().AddInternalReference(proto)
    prim.SetInstanceable(True)
    colour = Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(rgba[None, :3], np.float32))
    UsdGeom.PrimvarsAPI(prim).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
                                            UsdGeom.Tokens.constant).Set(colour)  # fmt: skip
    return prim


def matrix_instances(
    stage: Usd.Stage, job: ExportJob, wanted: np.ndarray, looks: list[UsdShade.Material], mat_of_row: np.ndarray
) -> np.ndarray:
    """Author the ``wanted`` rows that have a unit prototype; returns the mask of rows authored."""
    groups, _ = affine_groups(job, job.options["lod"])
    done = np.zeros(len(job.scene), bool)
    for group in groups:
        rows = group.rows[wanted[group.rows]]
        if not len(rows):
            continue
        mesh = group.proto.mesh
        proto = _prototype(stage, group.proto.key, mesh.positions, mesh.normals, mesh.indices)
        matrices = group.matrices[wanted[group.rows]]
        for row, affine in zip(rows.tolist(), matrices, strict=True):
            xf = UsdGeom.Xform.Define(
                stage, f"{ROOT}/Placed/{group.proto.key.replace('-', '_').replace('.', '_')}_{row}"
            )
            xf.AddTransformOp().Set(usd_matrix(affine))
            prim = xf.GetPrim()
            prim.GetReferences().AddInternalReference(proto)
            prim.SetInstanceable(True)
            rgba = job.scene.rgba[row]
            api = UsdGeom.PrimvarsAPI(prim)
            api.CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.constant).Set(
                Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(rgba[None, :3], np.float32)))  # fmt: skip
            bind(prim, looks[int(mat_of_row[row])])
        done[rows] = True
    return done
