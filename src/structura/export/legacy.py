"""The 1.5-compatible exporters: legacy OBJ layout and '.rendertemplate' text templates (docs/15 §5)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..core.params import ParamSpec, ParamType
from .base import Exporter, ExportJob, ExportReport, register
from .legacy_obj import LegacyObjExport
from .templates.engine import TemplateExport
from .templates.placeholders import TemplateCamera
from .templates.template_file import bundled_templates, load_template


class LegacyObjExporter(Exporter):
    name = "obj-legacy"
    title = "OBJ (Structure Synth 1.5 layout)"
    preferred = False
    extensions: tuple[str, ...] = (".obj",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("group_by_tag", ParamType.BOOL, False, "Group by tagging"),
        ParamSpec("group_by_color", ParamType.BOOL, False, "Group by colour"),
        ParamSpec("sphere_resolution", ParamType.INT, 10, "Sphere resolution (dt = dp)", range=(3, 100)),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        res = o["sphere_resolution"]
        exporter = LegacyObjExport(res, res, o["group_by_tag"], o["group_by_color"])
        path.write_text(exporter.render(job.scene), encoding="utf-8", newline="\n")
        return ExportReport(path, (path,), {"groups": len(exporter.groups)})


def template_camera(job: ExportJob, width: int, height: int) -> TemplateCamera:
    cam = job.model.camera
    _, right, up = cam.basis
    return TemplateCamera(_vec(np.asarray(cam.eye)), _vec(up), _vec(right), cam.target, width, height,
                          width / height, cam.fov_y_deg)  # fmt: skip


def _vec(v: np.ndarray) -> tuple[float, float, float]:
    return (float(v[0]), float(v[1]), float(v[2]))


class TemplateExporter(Exporter):
    name = "template"
    title = "Render template (.rendertemplate)"
    preferred = False  # .pov / .sc / .xml default to the modern scene writers
    extensions: tuple[str, ...] = (".pov", ".sc", ".rib", ".xml", ".txt")
    params: tuple[ParamSpec, ...] = (
        ParamSpec("template", ParamType.ENUM, "Sunflow-Colored", "Template", choices=tuple(bundled_templates())),
        ParamSpec("width", ParamType.INT, 640, "Width", range=(1, 65536)),
        ParamSpec("height", ParamType.INT, 480, "Height", range=(1, 65536)),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        template = load_template(bundled_templates()[o["template"]])
        export = TemplateExport(template, template_camera(job, o["width"], o["height"]), job.model.background)
        with path.open("w", encoding="utf-8", newline="\n") as out:
            for chunk in export.chunks(job.scene):
                job.check()
                out.write(chunk.replace("\r", ""))
        return ExportReport(path, (path,), {}, tuple(export.warnings))


register(LegacyObjExporter())
register(TemplateExporter())
