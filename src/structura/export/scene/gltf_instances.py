"""glTF instancing with EXT_mesh_gpu_instancing (docs/15 §4.2): one node per (kind, material) group whose
mesh is the unit prototype, with per-instance TRANSLATION / ROTATION / SCALE and a linear `_COLOR_0`
(read as the instance colour by three.js, Babylon.js and Blender ≥ 4.2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pygltflib as g

from ...core.color import srgb_to_linear
from ...core.geometry.tessellate import LOD
from ...core.geometry.unit_shapes import Mesh, unit_box, unit_sphere
from ...core.scene.ir import PrimitiveKind as K
from ..base import ExportJob
from .instancing import InstanceGroup

EXTENSION = "EXT_mesh_gpu_instancing"


def prototype(kind: K, lod: str) -> Mesh:
    """The unit box ([0, 1]³) or the unit sphere (centre 0, radius 1)."""
    if kind == K.BOX:
        return unit_box()
    s = unit_sphere(*LOD[lod])
    return Mesh((2 * s.positions - 1).astype(np.float32), s.normals, s.indices)


def _prototype_primitive(blob: Any, mesh: Mesh, material: int) -> g.Primitive:
    attrs = g.Attributes(
        POSITION=blob.accessor(mesh.positions, g.FLOAT, "VEC3", g.ARRAY_BUFFER, bounds=True),
        NORMAL=blob.accessor(mesh.normals, g.FLOAT, "VEC3", g.ARRAY_BUFFER),
    )
    indices = blob.accessor(mesh.indices.astype(np.uint32).ravel(), g.UNSIGNED_INT, "SCALAR", g.ELEMENT_ARRAY_BUFFER)
    return g.Primitive(attributes=attrs, indices=indices, material=material)


def _instance_attributes(blob: Any, group: InstanceGroup, job: ExportJob) -> dict[str, int]:
    rgba = job.scene.rgba[group.rows]
    colour = np.hstack([srgb_to_linear(rgba[:, :3]), rgba[:, 3:]]).astype(np.float32)
    return {
        "TRANSLATION": blob.accessor(group.translation, g.FLOAT, "VEC3", None),
        "ROTATION": blob.accessor(group.rotation, g.FLOAT, "VEC4", None),
        "SCALE": blob.accessor(group.scale, g.FLOAT, "VEC3", None),
        "_COLOR_0": blob.accessor(colour, g.FLOAT, "VEC4", None),
    }


def add_instanced_nodes(
    doc: g.GLTF2, blob: Any, job: ExportJob, groups: list[InstanceGroup], slot: Callable[[int], int]
) -> int:
    """Append a node per group to scene 0; ``slot`` maps a material-table index to a glTF material."""
    for group in groups:
        primitive = _prototype_primitive(blob, prototype(group.kind, job.options["lod"]), slot(group.material))
        doc.meshes.append(g.Mesh(name=f"{group.kind.name.title()}_{group.material}", primitives=[primitive]))
        ext = {EXTENSION: {"attributes": _instance_attributes(blob, group, job)}}
        doc.nodes.append(g.Node(name=doc.meshes[-1].name, mesh=len(doc.meshes) - 1, extensions=ext))
        doc.scenes[0].nodes.append(len(doc.nodes) - 1)
    return sum(len(group.rows) for group in groups)
