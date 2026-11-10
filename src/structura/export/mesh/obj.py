"""Wavefront OBJ + MTL (docs/15 §3): streamed per tessellation chunk, grouped, optional vertex colours."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from ...core.geometry.tessellate import TessOptions, iter_tessellate
from ...core.geometry.trimesh import TriMesh
from ...core.params import ParamSpec, ParamType
from ...core.scene.material import Material
from ..base import Exporter, ExportJob, ExportReport, register
from ..csg import export_mesh
from .ascii import face_rows, float_rows
from .grouping import GROUPINGS, group_keys, hex_color
from .meshlab import MESHLAB_OPTIONS

COMMON = (
    ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
    ParamSpec("up", ParamType.ENUM, "y", "Up axis", choices=("y", "z")),
    ParamSpec("unit_scale", ParamType.FLOAT, 1.0, "Unit scale", range=(1e-6, 1e6)),
)


def _mtl(name: str, material: Material | None) -> str:
    rgb = hex_color(name)
    base = rgb or (material.base if material is not None and not material.uses_state_color else (0.8, 0.8, 0.8))
    m = material or Material()
    shininess = max(1.0, 1000.0 * (1.0 - m.roughness) ** 2)
    lines = [
        f"newmtl {name}",
        f"Kd {base[0]:.6g} {base[1]:.6g} {base[2]:.6g}",
        f"Ks {m.specular * 0.08:.6g} {m.specular * 0.08:.6g} {m.specular * 0.08:.6g}",
        f"Ns {shininess:.6g}",
        f"Ni {m.ior:.6g}",
        f"d {1.0 - m.transmission:.6g}",
        f"Pr {m.roughness:.6g}",
        f"Pm {m.metallic:.6g}",
        "illum 2",
    ]
    return "\n".join(lines) + "\n\n"


class ObjExporter(Exporter):
    name = "obj"
    title = "Wavefront OBJ"
    extensions: tuple[str, ...] = (".obj",)
    params: tuple[ParamSpec, ...] = (
        *COMMON,
        ParamSpec("grouping", ParamType.ENUM, "color", "Group by", choices=GROUPINGS),
        ParamSpec("vertex_colors", ParamType.BOOL, True, "Vertex colours (v x y z r g b)"),
        ParamSpec("normals", ParamType.BOOL, True, "Normals"),
        *MESHLAB_OPTIONS,
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        model = job.model
        mtl_path = path.with_suffix(".mtl")
        groups: dict[str, Material | None] = {}
        counts = {"vertices": 0, "triangles": 0}
        with path.open("wb") as out:
            out.write(f"# Structura OBJ export\nmtllib {mtl_path.name}\n".encode())
            for chunk in self._chunks(job):
                job.check()
                self._chunk(out, chunk, job, groups, counts)
                job.progress(0.0, f"{counts['triangles']:,} triangles")
        by_name = {m.name: m for m in model.materials.materials}
        mtl_path.write_text("".join(_mtl(g, by_name.get(g)) for g in groups), encoding="utf-8")
        return ExportReport(path, (path, mtl_path), counts)

    @staticmethod
    def _chunks(job: ExportJob) -> Iterator[TriMesh]:
        """Tessellation chunks as they come (streamed), or one cleaned-up mesh (a clean-up needs it all)."""
        if job.options["cleanup"] == "none":
            yield from iter_tessellate(job.scene, TessOptions(lod=job.options["lod"]))
            return
        yield export_mesh(job)[0]

    def _chunk(self, out: io.BufferedIOBase, chunk: TriMesh, job: ExportJob, groups: dict, counts: dict) -> None:  # type: ignore[type-arg]
        if not chunk.triangles:
            return
        o, model = job.options, job.model
        pos = model.points(chunk.positions)
        if o["vertex_colors"]:
            out.write(float_rows("v", np.hstack([pos, chunk.colors[:, :3]]), (6, 6, 6, 4, 4, 4)))
        else:
            out.write(float_rows("v", pos, (6, 6, 6)))
        if o["normals"]:
            out.write(float_rows("vn", model.directions(chunk.normals), (4, 4, 4)))
        keys = group_keys(chunk, job.scene, model.materials, o["grouping"])
        order = np.argsort(keys, kind="stable")
        for key in dict.fromkeys(keys[order]):
            groups.setdefault(str(key), None)
            out.write(f"g {key}\nusemtl {key}\n".encode())
            out.write(face_rows(chunk.indices[keys == key], counts["vertices"], o["normals"]))
        counts["vertices"] += len(pos)
        counts["triangles"] += chunk.triangles


register(ObjExporter())
