"""Group triangles for formats with groups/materials: none, tag, colour or material (docs/15 §2.3)."""

from __future__ import annotations

import numpy as np

from ...core.geometry.tessellate import TriMesh
from ...core.scene.ir import SceneIR
from ...core.scene.material_library import MaterialTable

GROUPINGS = ("none", "tag", "color", "material")


def group_keys(mesh: TriMesh, scene: SceneIR, materials: MaterialTable, grouping: str) -> np.ndarray:
    """A group name per triangle."""
    owners = mesh.owners
    if grouping == "tag":
        names = np.array([t or "default" for t in scene.tags], dtype=object)
        by_tag: np.ndarray = names[scene.tag[owners]]
        return by_tag
    if grouping == "material":
        mats = np.array([m.name for m in materials.materials], dtype=object)
        by_material: np.ndarray = mats[materials.by_tag[scene.tag[owners]]]
        return by_material
    if grouping == "color":
        rgb = np.clip(np.rint(scene.rgba[owners, :3] * 255), 0, 255).astype(np.int64)
        packed = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
        return np.array([f"c{v:06x}" for v in packed], dtype=object)
    return np.full(len(owners), "default", dtype=object)


def hex_color(name: str) -> tuple[float, float, float] | None:
    """The colour encoded in a 'cRRGGBB' group name."""
    if len(name) == 7 and name.startswith("c"):
        v = int(name[1:], 16)
        return ((v >> 16) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255)
    return None
