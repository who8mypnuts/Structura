"""MeshLab project (.mlp; PLAN Q4): one PLY layer per tag, material or colour, listed in a project MeshLab
opens as separate layers — for per-part cleaning, measuring and colouring there. The layers go into a
'<name>_layers' folder beside the project; the MeshLab clean-up options apply before the split."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register
from ..csg import CSG_OPTION, export_mesh
from .grouping import GROUPINGS, group_keys
from .meshlab import MESHLAB_OPTIONS
from .obj import COMMON
from .ply import ply_bytes

IDENTITY = "\n1 0 0 0 \n0 1 0 0 \n0 0 1 0 \n0 0 0 1 \n"
UNSAFE = re.compile(r"[^\w.-]+")


def layer_name(key: str) -> str:
    return UNSAFE.sub("_", key).strip("_") or "layer"


def project_xml(layers: list[tuple[str, str]]) -> str:
    """The .mlp document for (label, relative PLY path) layers."""
    root = ET.Element("MeshLabProject")
    group = ET.SubElement(root, "MeshGroup")
    for label, filename in layers:
        mesh = ET.SubElement(group, "MLMesh", label=label, filename=filename, visible="1")
        ET.SubElement(mesh, "MLMatrix44").text = IDENTITY
    ET.SubElement(root, "RasterGroup")
    return "<!DOCTYPE MeshLabDocument>\n" + ET.tostring(root, encoding="unicode") + "\n"


class MeshLabProjectExporter(Exporter):
    name = "meshlab"
    title = "MeshLab project (.mlp + PLY layers)"
    extensions: tuple[str, ...] = (".mlp",)
    params: tuple[ParamSpec, ...] = (
        *COMMON,
        ParamSpec("grouping", ParamType.ENUM, "material", "One layer per", choices=GROUPINGS),
        CSG_OPTION,
        *MESHLAB_OPTIONS,
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        mesh, warnings = export_mesh(job)
        job.check()
        keys = group_keys(mesh, job.scene, job.model.materials, job.options["grouping"])
        folder = path.with_name(f"{path.stem}_layers")
        folder.mkdir(parents=True, exist_ok=True)
        layers, files = [], []
        for key in dict.fromkeys(keys.tolist()):
            part = mesh.select(np.asarray(keys == key))
            target = folder / f"{layer_name(str(key))}.ply"
            target.write_bytes(ply_bytes(part, job.model.points(part.positions), job.model.directions(part.normals)))
            layers.append((str(key), f"{folder.name}/{target.name}"))
            files.append(target)
        path.write_text(project_xml(layers), encoding="utf-8")
        counts = {"layers": len(layers), "triangles": mesh.triangles}
        return ExportReport(path, (path, *files), counts, warnings)


register(MeshLabProjectExporter())
