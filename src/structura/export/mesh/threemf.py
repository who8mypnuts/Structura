"""3MF (3D Manufacturing Format) for colour 3D printing (docs/15 §3, M8): one mesh object, per-triangle
colours through a `basematerials` group, millimetre units, placed on the build plate."""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.params import ParamSpec, ParamType
from ..base import Exporter, ExportJob, ExportReport, register

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    "</Types>"
)
RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
)


def palette(rgba: np.ndarray) -> tuple[list[str], np.ndarray]:
    """Unique '#RRGGBBAA' strings and the palette index of every row."""
    q = np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)
    packed = np.ascontiguousarray(q).view(">u4").reshape(-1)
    unique, index = np.unique(packed, return_inverse=True)
    return [f"#{int(v):08X}" for v in unique], index.reshape(-1)


def model_xml(points: np.ndarray, tris: np.ndarray, colours: list[str], tri_colour: np.ndarray) -> str:
    """The 3D/3dmodel.model document (vertices in mm)."""
    verts = "".join(f'<vertex x="{x:.6g}" y="{y:.6g}" z="{z:.6g}"/>' for x, y, z in points.tolist())
    rows = zip(tris.tolist(), tri_colour.tolist(), strict=True)
    faces = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" p1="{p}"/>' for (a, b, c), p in rows)
    bases = "".join(f'<base name="{c}" displaycolor="{c}"/>' for c in colours)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="{NS}">'
        '<metadata name="Application">Structura</metadata>'
        f'<resources><basematerials id="1">{bases}</basematerials>'
        f'<object id="2" type="model" pid="1" pindex="0"><mesh><vertices>{verts}</vertices>'
        f"<triangles>{faces}</triangles></mesh></object></resources>"
        '<build><item objectid="2"/></build></model>'
    )


def write_3mf(path: Path, model: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)


class ThreeMfExporter(Exporter):
    name = "3mf"
    title = "3MF (colour 3D printing)"
    extensions: tuple[str, ...] = (".3mf",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 10.0, "Millimetres per unit", range=(1e-6, 1e6)),
        ParamSpec("on_plate", ParamType.BOOL, True, "Place on the build plate (min z = 0)"),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        mesh = tessellate(job.scene, TessOptions(lod=o["lod"]))
        job.check()
        points = job.model.points(mesh.positions).astype(np.float64)
        if o["on_plate"] and len(points):
            points[:, 2] -= points[:, 2].min()
        colours, index = palette(job.scene.rgba[mesh.owners])
        write_3mf(path, model_xml(points, mesh.indices, colours, index))
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles})


register(ThreeMfExporter())
