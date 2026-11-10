"""USD authoring helpers: stage, materials (UsdPreviewSurface driven by displayColor), camera (docs/15 §4.1)."""

from __future__ import annotations

import math

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from ...core.scene.material import Material
from ..scene_model import ExportSceneModel

ROOT = "/Structura"


def new_stage(path: str, model: ExportSceneModel) -> Usd.Stage:
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z if model.up == "z" else UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0 / model.unit_scale)
    root = UsdGeom.Xform.Define(stage, ROOT)
    stage.SetDefaultPrim(root.GetPrim())
    return stage


def safe_name(name: str, fallback: str) -> str:
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    return cleaned if cleaned and not cleaned[0].isdigit() else f"{fallback}_{cleaned}"


def material(stage: Usd.Stage, m: Material, index: int) -> UsdShade.Material:
    path = f"{ROOT}/Looks/{safe_name(m.name, 'Material')}_{index}"
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"{path}/DisplayColor")
    reader.CreateIdAttr("UsdPrimvarReader_float3")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
    color = reader.CreateOutput("result", Sdf.ValueTypeNames.Float3)
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(color)
    inputs = {"metallic": m.metallic, "roughness": m.roughness, "ior": m.ior, "opacity": 1.0 - m.transmission,
              "clearcoat": m.coat, "clearcoatRoughness": m.coat_roughness}  # fmt: skip
    for name, value in inputs.items():
        shader.CreateInput(name, Sdf.ValueTypeNames.Float).Set(float(value))
    if m.emission_strength > 0:
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*([m.emission_strength] * 3)))
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def bind(prim: Usd.Prim, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def display_colors(prim: UsdGeom.Imageable, rgba: np.ndarray, interpolation: str) -> None:
    """primvars:displayColor (+ displayOpacity when needed); works for gprims and PointInstancers alike."""
    api = UsdGeom.PrimvarsAPI(prim.GetPrim())
    colors = np.ascontiguousarray(rgba[:, :3], np.float32)
    api.CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray, interpolation).Set(
        Vt.Vec3fArray.FromNumpy(colors)
    )
    if (rgba[:, 3] < 1).any():
        opacity = np.ascontiguousarray(rgba[:, 3], np.float32)
        api.CreatePrimvar("displayOpacity", Sdf.ValueTypeNames.FloatArray, interpolation).Set(
            Vt.FloatArray.FromNumpy(opacity)
        )


def camera(stage: Usd.Stage, model: ExportSceneModel) -> None:
    cam = model.camera
    lens = cam.lens
    usd_cam = UsdGeom.Camera.Define(stage, f"{ROOT}/Camera")
    sensor_h = lens.sensor_mm[1]  # the camera's own sensor: focal length, apertures and shift in mm
    usd_cam.CreateFocalLengthAttr(cam.focal_length_mm)
    usd_cam.CreateVerticalApertureAttr(sensor_h)
    usd_cam.CreateHorizontalApertureAttr(sensor_h * model.aspect)
    usd_cam.CreateHorizontalApertureOffsetAttr(lens.shift[0] * sensor_h)
    usd_cam.CreateVerticalApertureOffsetAttr(lens.shift[1] * sensor_h)
    usd_cam.CreateFocusDistanceAttr(float(cam.focus * model.unit_scale))
    if cam.aperture_radius > 0 and math.isfinite(cam.fstop):
        usd_cam.CreateFStopAttr(float(cam.fstop))
    if lens.projection == "orthographic":
        usd_cam.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
    eye = model.points(np.asarray(cam.eye, np.float32)[None])[0]
    target = model.points(np.asarray(cam.target, np.float32)[None])[0]
    up = model.directions(np.asarray(cam.up, np.float32)[None])[0]
    view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye.tolist()), Gf.Vec3d(*target.tolist()), Gf.Vec3d(*up.tolist()))
    usd_cam.AddTransformOp().Set(view.GetInverse())
