"""Text scene exporters (docs/15 §4.4): POV-Ray 3.8, Sunflow and Mitsuba 3, from one context (text_scene.py)
and one Jinja2 template each. All three place unit prototypes with full matrices, so nothing is baked
except lines, dots, grids, meshes and triangles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import numpy as np

from ...core.geometry.trimesh import TriMesh
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register
from ..mesh.ply import ply_bytes
from .text_scene import Placed, render_template, text_scene

SIZE = (
    ParamSpec("lod", ParamType.ENUM, "medium", "Detail of baked parts", choices=("low", "medium", "high", "ultra")),
    ParamSpec("width", ParamType.INT, 800, "Image width", range=(1, 65536)),
    ParamSpec("height", ParamType.INT, 600, "Image height", range=(1, 65536)),
)


class TextSceneExporter(Exporter):
    template: ClassVar[str] = ""

    def context(self, job: ExportJob, path: Path) -> dict[str, Any]:
        o = job.options
        return text_scene(job, o["lod"]) | {"width": o["width"], "height": o["height"]}

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        context = self.context(job, path)
        job.check()
        path.write_text(render_template(self.template, context), encoding="utf-8")
        counts = {"instances": len(context["placed"]), "shaders": len(context["shaders"])}
        return ExportReport(path, (path, *context.get("files", ())), counts)


class PovRayExporter(TextSceneExporter):
    name = "povray"
    title = "POV-Ray 3.8 scene"
    extensions: tuple[str, ...] = (".pov",)
    template = "povray.pov.j2"
    params: tuple[ParamSpec, ...] = (*SIZE, ParamSpec("radiosity", ParamType.BOOL, True, "Radiosity (GI)"),
                                     ParamSpec("ambient_sky", ParamType.BOOL, True, "Sky sphere"))  # fmt: skip

    def context(self, job: ExportJob, path: Path) -> dict[str, Any]:
        return super().context(job, path) | {"radiosity": job.options["radiosity"],
                                             "ambient_sky": job.options["ambient_sky"]}  # fmt: skip


class SunflowExporter(TextSceneExporter):
    name = "sunflow"
    title = "Sunflow scene (.sc)"
    extensions: tuple[str, ...] = (".sc",)
    template = "sunflow.sc.j2"
    params: tuple[ParamSpec, ...] = SIZE


def _white(positions: np.ndarray, normals: np.ndarray, indices: np.ndarray) -> TriMesh:
    colours = np.ones((len(positions), 4), np.float32)
    return TriMesh(positions, normals, colours, indices, np.zeros(len(indices), np.int64))


class MitsubaExporter(TextSceneExporter):
    name = "mitsuba"
    title = "Mitsuba 3 scene (.xml)"
    extensions: tuple[str, ...] = (".xml",)
    template = "mitsuba.xml.j2"
    params: tuple[ParamSpec, ...] = (*SIZE, ParamSpec("samples", ParamType.INT, 64, "Samples", range=(1, 65536)))

    def context(self, job: ExportJob, path: Path) -> dict[str, Any]:
        """Mitsuba reads meshes from files: the prototypes and the baked part go to '<name>_meshes/'."""
        context = super().context(job, path)
        folder = path.with_name(f"{path.stem}_meshes")
        folder.mkdir(exist_ok=True)
        files = []
        for proto in context["prototypes"]:
            m = proto.mesh
            target = folder / f"P_{proto.key.replace('-', '_').replace('.', '_')}.ply"
            target.write_bytes(ply_bytes(_white(m.positions, m.normals, m.indices), m.positions, m.normals))
            files.append(target)
        if context["rest"] is not None:
            rest = context["rest"]
            (folder / "baked.ply").write_bytes(ply_bytes(rest["mesh"], rest["points"], rest["normals"]))
            files.append(folder / "baked.ply")
        return context | {"mesh_dir": folder.name, "groups": _groups(context["placed"]), "files": tuple(files),
                          "samples": job.options["samples"]}  # fmt: skip


def _groups(placed: list[Placed]) -> list[dict[str, str]]:
    """One shapegroup per (prototype, shader) pair in use."""
    seen: dict[str, dict[str, str]] = {}
    for i in placed:
        ident = i.proto.key.replace("-", "_").replace(".", "_")
        gid = f"G_{ident}_{i.shader}"
        seen.setdefault(gid, {"id": gid, "ply": f"P_{ident}.ply", "shader": i.shader})
    return list(seen.values())


register(PovRayExporter())
register(SunflowExporter())
register(MitsubaExporter())
