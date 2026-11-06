"""Blender script export (docs/15 §4.3): a self-contained Python script for Blender ≥ 4.2 plus an .npz
sidecar with baked meshes per material (vertex colours in a 'Col' attribute), the camera and the world."""

from __future__ import annotations

import json
import math
from pathlib import Path

import jinja2
import numpy as np

from ...core.color import srgb_to_linear
from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register

TEMPLATE = Path(__file__).resolve().parent / "blender_script.py.j2"
SENSOR_WIDTH = 36.0  # mm


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
    fov_x = 2 * math.atan(math.tan(math.radians(cam.fov_y_deg) / 2) * job.model.aspect)
    lens = 0.5 * SENSOR_WIDTH / math.tan(fov_x / 2)
    return {"eye": eye.tolist(), "target": target.tolist(), "lens": lens, "focus": cam.focus * job.model.unit_scale}


class BlenderExporter(Exporter):
    name = "blender"
    title = "Blender script (.py + .npz)"
    extensions: tuple[str, ...] = (".py",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 1.0, "Unit scale", range=(1e-6, 1e6)),
        ParamSpec("samples", ParamType.INT, 128, "Cycles samples", range=(1, 65536)),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        model = job.model.__class__(**{**job.model.__dict__, "up": "z"})  # Blender is Z-up
        job = ExportJob(job.scene, model, job.options, job.progress, job.cancelled)
        mesh = tessellate(job.scene, TessOptions(lod=job.options["lod"]))
        job.check()
        table = model.materials
        mat_of_tri = table.by_tag[job.scene.tag[mesh.owners]] if mesh.triangles else np.zeros(0, np.int32)
        arrays: dict[str, np.ndarray] = {}
        for index in np.unique(mat_of_tri):
            tri = mesh.indices[mat_of_tri == index]
            used, remap = np.unique(tri, return_inverse=True)
            colors = np.hstack([srgb_to_linear(mesh.colors[used, :3]), mesh.colors[used, 3:]])
            arrays[f"m{index}_points"] = model.points(mesh.positions[used])
            arrays[f"m{index}_faces"] = remap.reshape(-1, 3).astype(np.int32)
            arrays[f"m{index}_colors"] = colors.astype(np.float32)
        sidecar = path.with_suffix(".npz")
        np.savez_compressed(sidecar, allow_pickle=False, **arrays)
        background = [float(c) for c in srgb_to_linear(np.asarray(model.background, np.float32))]
        scene = {"materials": _materials(job), "camera": _camera(job), "samples": job.options["samples"],
                 "background": background}  # fmt: skip
        script = jinja2.Template(TEMPLATE.read_text(encoding="utf-8")).render(
            sidecar=sidecar.name, scene_json=json.dumps(scene, indent=1)
        )
        path.write_text(script, encoding="utf-8")
        return ExportReport(path, (path, sidecar), {"triangles": mesh.triangles, "materials": len(arrays) // 3})


register(BlenderExporter())
