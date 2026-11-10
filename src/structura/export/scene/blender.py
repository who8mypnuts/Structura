"""Blender script export (docs/15 §4.3): a self-contained Python script for Blender ≥ 4.2 plus an .npz
sidecar, the camera and the world.

*baked* (default): meshes per material with vertex colours in a 'Col' attribute. *instanced*: every
prototype-placeable instance (boxes, spheres, the v2 solids) becomes a point of a point cloud whose Geometry
Nodes modifier instances the unit prototype, with 'rotation' (quaternion) and 'scale' point attributes from
the TRS decomposition and the colour in 'Col' (read per instance by the material). Sheared instances and the
other kinds stay baked."""

from __future__ import annotations

import json
import math
from pathlib import Path

import jinja2
import numpy as np

from ...core.color import srgb_to_linear
from ...core.geometry.affine import decompose
from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.params import ParamSpec, ParamType
from ..affine_instances import affine_groups
from ..base import Exporter, ExportJob, ExportReport, register

TEMPLATE = Path(__file__).resolve().parent / "blender_script.py.j2"


def _materials(job: ExportJob) -> list[dict[str, object]]:
    return [
        {"name": m.name, "metallic": m.metallic, "roughness": m.roughness, "ior": m.ior,
         "transmission": m.transmission, "coat": m.coat, "coat_roughness": m.coat_roughness,
         "emission": m.emission_strength, "anisotropy": m.anisotropy}
        for m in job.model.materials.materials
    ]  # fmt: skip


def _camera(job: ExportJob) -> dict[str, object]:
    cam = job.model.camera
    eye = job.model.points(np.asarray(cam.eye, np.float32)[None])[0]
    target = job.model.points(np.asarray(cam.target, np.float32)[None])[0]
    lens, aspect = cam.lens, job.model.aspect
    spec: dict[str, object] = {
        "eye": eye.tolist(), "target": target.tolist(), "lens": cam.focal_length_mm, "sensor_height": lens.sensor_mm[1],
        "focus": cam.focus * job.model.unit_scale, "shift": [s / max(aspect, 1.0) for s in lens.shift],
        "ortho_scale": lens.ortho_height * max(aspect, 1.0) * job.model.unit_scale,
        "projection": lens.projection, "fisheye_fov": math.radians(lens.fisheye_fov_deg),
    }  # Blender's shift and ortho scale are in fractions / lengths of the frame's larger side  # fmt: skip
    if cam.aperture_radius > 0 and math.isfinite(cam.fstop):
        spec["dof"] = {"fstop": cam.fstop, "blades": lens.blades, "rotation": math.radians(lens.blade_rotation_deg),
                       "ratio": lens.anamorphic}  # fmt: skip
    return spec


class BlenderExporter(Exporter):
    name = "blender"
    title = "Blender script (.py + .npz)"
    extensions: tuple[str, ...] = (".py",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 1.0, "Unit scale", range=(1e-6, 1e6)),
        ParamSpec("samples", ParamType.INT, 128, "Cycles samples", range=(1, 65536)),
        ParamSpec("geometry", ParamType.ENUM, "baked", "Geometry", choices=("baked", "instanced")),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        model = job.model.__class__(**{**job.model.__dict__, "up": "z"})  # Blender is Z-up
        job = ExportJob(job.scene, model, job.options, job.progress, job.cancelled)
        arrays: dict[str, np.ndarray] = {}
        instanced: list[dict[str, object]] = []
        rest = np.ones(len(job.scene), bool)
        if job.options["geometry"] == "instanced":
            instanced, placed = instanced_arrays(job, arrays)
            rest &= ~placed
        triangles = baked_arrays(job, rest, arrays)
        job.check()
        sidecar = path.with_suffix(".npz")
        np.savez_compressed(sidecar, allow_pickle=False, **arrays)
        background = [float(c) for c in srgb_to_linear(np.asarray(model.background, np.float32))]
        scene = {"materials": _materials(job), "camera": _camera(job), "samples": job.options["samples"],
                 "background": background, "instanced": instanced}  # fmt: skip
        script = jinja2.Template(TEMPLATE.read_text(encoding="utf-8")).render(
            sidecar=sidecar.name, scene_json=json.dumps(scene, indent=1)
        )
        path.write_text(script, encoding="utf-8")
        counts = {"triangles": triangles, "materials": sum(k.endswith("_points") for k in arrays if k[0] == "m"),
                  "instanced": int((~rest).sum())}  # fmt: skip
        return ExportReport(path, (path, sidecar), counts)


def baked_arrays(job: ExportJob, rows: np.ndarray, arrays: dict[str, np.ndarray]) -> int:
    """Meshes per material for the ``rows`` mask: m<i>_points / _faces / _colors. Returns the triangle count."""
    sub = job.scene.subset(np.nonzero(rows)[0])
    mesh = tessellate(sub, TessOptions(lod=job.options["lod"]))
    table = job.model.materials
    mat_of_tri = table.by_tag[sub.tag[mesh.owners]] if mesh.triangles else np.zeros(0, np.int32)
    for index in np.unique(mat_of_tri):
        tri = mesh.indices[mat_of_tri == index]
        used, remap = np.unique(tri, return_inverse=True)
        colors = np.hstack([srgb_to_linear(mesh.colors[used, :3]), mesh.colors[used, 3:]])
        arrays[f"m{index}_points"] = job.model.points(mesh.positions[used])
        arrays[f"m{index}_faces"] = remap.reshape(-1, 3).astype(np.int32)
        arrays[f"m{index}_colors"] = colors.astype(np.float32)
    return mesh.triangles


def instanced_arrays(job: ExportJob, arrays: dict[str, np.ndarray]) -> tuple[list[dict[str, object]], np.ndarray]:
    """One point cloud per (prototype, material): g<i>_proto_points / _proto_faces / _location / _rotation
    (w, x, y, z) / _scale / _colors. Returns the cloud descriptions and the mask of rows they place."""
    groups, _ = affine_groups(job, job.options["lod"])
    table, scene = job.model.materials, job.scene
    mat_of_row = table.by_tag[scene.tag] if len(scene) else np.zeros(0, np.int32)
    clouds: list[dict[str, object]] = []
    placed = np.zeros(len(scene), bool)
    for group in groups:
        trs = decompose(group.matrices)
        ok = trs.representable()
        for m in np.unique(mat_of_row[group.rows[ok]]):
            take = ok & (mat_of_row[group.rows] == m)
            key = f"g{len(clouds)}"
            arrays[f"{key}_proto_points"] = group.proto.mesh.positions.astype(np.float32)
            arrays[f"{key}_proto_faces"] = group.proto.mesh.indices.astype(np.int32)
            arrays[f"{key}_location"] = trs.translation[take]
            arrays[f"{key}_rotation"] = trs.rotation[take][:, [3, 0, 1, 2]].astype(np.float32)
            arrays[f"{key}_scale"] = trs.scale[take]
            rgba = scene.rgba[group.rows[take]]
            arrays[f"{key}_colors"] = np.hstack([srgb_to_linear(rgba[:, :3]), rgba[:, 3:]]).astype(np.float32)
            clouds.append({"key": key, "prototype": group.proto.key, "material": int(m)})
            placed[group.rows[take]] = True
    return clouds, placed


register(BlenderExporter())
