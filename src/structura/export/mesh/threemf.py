"""3MF (3D Manufacturing Format) for colour 3D printing (docs/15 §3): millimetre units, placed on the build
plate, colours through one `basematerials` group.

Two layouts: *baked* — one mesh object with per-triangle colours; *instanced* (the default) — one prototype
object per (shape, colour), placed by the `components` of one assembly object with full affine transforms
(so sheared instances need no baking), and the remaining kinds (lines, grids, meshes …) baked alongside.
A slicer sees one object either way.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.params import ParamSpec, ParamType
from ..affine_instances import AffineGroup, affine_groups
from ..base import Exporter, ExportJob, ExportReport, register
from ..csg import CSG_OPTION, export_mesh, has_markers
from .meshlab import MESHLAB_OPTIONS

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
PALETTE_ID = 1


def palette(rgba: np.ndarray) -> tuple[list[str], np.ndarray]:
    """Unique '#RRGGBBAA' strings and the palette index of every row."""
    q = np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)
    packed = np.ascontiguousarray(q).view(">u4").reshape(-1)
    unique, index = np.unique(packed, return_inverse=True)
    return [f"#{int(v):08X}" for v in unique], index.reshape(-1)


def mesh_xml(points: np.ndarray, tris: np.ndarray, tri_colour: np.ndarray | None = None) -> str:
    verts = "".join(f'<vertex x="{x:.6g}" y="{y:.6g}" z="{z:.6g}"/>' for x, y, z in points.tolist())
    if tri_colour is None:
        faces = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris.tolist())
    else:
        rows = zip(tris.tolist(), tri_colour.tolist(), strict=True)
        faces = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" p1="{p}"/>' for (a, b, c), p in rows)
    return f"<mesh><vertices>{verts}</vertices><triangles>{faces}</triangles></mesh>"


def transform(matrix: np.ndarray) -> str:
    """A column-vector affine (3×4) in 3MF's row-vector form 'm00 m01 m02 … m30 m31 m32'."""
    rows = np.vstack([matrix[:, :3].T, matrix[:, 3]])
    return " ".join(f"{v:.9g}" for v in rows.ravel().tolist())


def document(colours: list[str], objects: str, item: str) -> str:
    bases = "".join(f'<base name="{c}" displaycolor="{c}"/>' for c in colours)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="{NS}">'
        '<metadata name="Application">Structura</metadata>'
        f'<resources><basematerials id="{PALETTE_ID}">{bases}</basematerials>{objects}</resources>'
        f"<build>{item}</build></model>"
    )


def write_3mf(path: Path, model: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)


def _plate(on_plate: bool, z_min: float) -> str:
    return f' transform="1 0 0 0 1 0 0 0 1 0 0 {-z_min:.9g}"' if on_plate and np.isfinite(z_min) else ""


def _instance_min_z(group: AffineGroup) -> float:
    points = np.einsum("nij,vj->nvi", group.matrices[:, :, :3], group.proto.mesh.positions)
    return float((points[:, :, 2] + group.matrices[:, None, 2, 3]).min()) if len(points) else np.inf


class _Instanced:
    """Builds the instanced document: prototype objects per (shape, colour), then the baked rest."""

    def __init__(self, job: ExportJob, lod: str) -> None:
        self.job = job
        self.groups, covered = affine_groups(job, lod)
        self.rest_rows = np.nonzero(~covered)[0]
        self.rest = tessellate(job.scene.subset(self.rest_rows), TessOptions(lod=lod))
        self.rest_points = job.model.points(self.rest.positions)
        self.colours, self.index = palette(job.scene.rgba)
        self.counts = {"instances": int(covered.sum()), "prototypes": 0, "triangles": self.rest.triangles}

    def objects(self) -> Iterator[tuple[int, str, str]]:
        """(object id, object XML, component XML) per prototype and colour, then the baked rest."""
        next_id = PALETTE_ID + 1
        for group in self.groups:
            colour_of = self.index[group.rows]
            body = mesh_xml(group.proto.mesh.positions, group.proto.mesh.indices)
            for colour in np.unique(colour_of):
                take = colour_of == colour
                obj = f'<object id="{next_id}" type="model" pid="{PALETTE_ID}" pindex="{colour}">{body}</object>'
                parts = "".join(f'<component objectid="{next_id}" transform="{transform(m)}"/>'
                                for m in group.matrices[take])  # fmt: skip
                self.counts["prototypes"] += 1
                self.counts["triangles"] += group.proto.mesh.triangles * int(take.sum())
                yield next_id, obj, parts
                next_id += 1
        if self.rest.triangles:
            tri_colour = self.index[self.rest_rows[self.rest.owners]]
            body = mesh_xml(self.rest_points, self.rest.indices, tri_colour)
            obj = f'<object id="{next_id}" type="model" pid="{PALETTE_ID}" pindex="0">{body}</object>'
            yield next_id, obj, f'<component objectid="{next_id}"/>'

    def z_min(self) -> float:
        zs = [_instance_min_z(g) for g in self.groups]
        return min([*zs, float(self.rest_points[:, 2].min(initial=np.inf))])


class ThreeMfExporter(Exporter):
    """3MF for colour 3D printing, with instanced components."""

    name = "3mf"
    title = "3MF (colour 3D printing)"
    extensions: tuple[str, ...] = (".3mf",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 10.0, "Millimetres per unit", range=(1e-6, 1e6)),
        ParamSpec("on_plate", ParamType.BOOL, True, "Place on the build plate (min z = 0)"),
        ParamSpec("instancing", ParamType.BOOL, True, "Instanced components (smaller files; off with a clean-up)"),
        CSG_OPTION,
        *MESHLAB_OPTIONS,
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        o = job.options
        if o["instancing"] and o["cleanup"] == "none" and not (o["csg"] and has_markers(job.scene)):
            return self._instanced(job, path)
        mesh, warnings = export_mesh(job)
        job.check()
        points = job.model.points(mesh.positions).astype(np.float64)
        z_min = float(points[:, 2].min()) if len(points) else np.inf
        colours, index = palette(mesh.colors[mesh.indices[:, 0]])
        obj = f'<object id="2" type="model" pid="{PALETTE_ID}" pindex="0">{mesh_xml(points, mesh.indices, index)}'
        item = f'<item objectid="2"{_plate(o["on_plate"], z_min)}/>'
        write_3mf(path, document(colours, obj + "</object>", item))
        return ExportReport(path, (path,), {"vertices": len(points), "triangles": mesh.triangles}, warnings)

    def _instanced(self, job: ExportJob, path: Path) -> ExportReport:
        built = _Instanced(job, job.options["lod"])
        pieces = list(built.objects())
        job.check()
        assembly = max((i for i, _, _ in pieces), default=PALETTE_ID) + 1
        parts = "".join(p for _, _, p in pieces)
        objects = "".join(o for _, o, _ in pieces) + (
            f'<object id="{assembly}" type="model"><components>{parts}</components></object>'
        )
        item = f'<item objectid="{assembly}"{_plate(job.options["on_plate"], built.z_min())}/>'
        write_3mf(path, document(built.colours, objects, item))
        return ExportReport(path, (path,), built.counts)


register(ThreeMfExporter())
