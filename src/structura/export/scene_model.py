"""ExportSceneModel: what every scene-level exporter needs, built once per export (docs/15 §1, §2.3).

Structura's world is right-handed, Y-up, 1 unit = 1 m. ``up`` = "z" converts to Z-up (Blender, 3D
printing) with one matrix; ``unit_scale`` multiplies lengths.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.scene.camera import Camera, framed
from ..core.scene.ir import SceneIR
from ..core.scene.material_library import MaterialTable, resolve_materials
from ..core.scene.settings import settings_from_events

Y_TO_Z = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]], np.float32)


@dataclass(frozen=True)
class ExportSceneModel:
    camera: Camera
    background: tuple[float, float, float]  # sRGB
    materials: MaterialTable
    up: str = "y"
    unit_scale: float = 1.0
    aspect: float = 4 / 3

    @property
    def axes(self) -> np.ndarray:
        """3×3 matrix from Structura world axes to the output's axes (including the unit scale)."""
        base = Y_TO_Z if self.up == "z" else np.eye(3, dtype=np.float32)
        return (base * np.float32(self.unit_scale)).astype(np.float32)

    def points(self, p: np.ndarray) -> np.ndarray:
        out: np.ndarray = (p @ self.axes.T).astype(np.float32)
        return out

    def directions(self, d: np.ndarray) -> np.ndarray:
        out: np.ndarray = (d @ (self.axes / np.float32(self.unit_scale)).T).astype(np.float32)
        return out

    def xforms(self, xform: np.ndarray) -> np.ndarray:
        """(N,3,4) world affines in the output's axes and units: [A·L | A·t] (A = axes)."""
        a = self.axes
        linear = np.einsum("ij,njk->nik", a, xform[:, :, :3])
        return np.concatenate([linear, np.einsum("ij,nj->ni", a, xform[:, :, 3])[:, :, None]], axis=2)


def scene_model(
    scene: SceneIR, camera: Camera | None = None, up: str = "y", unit_scale: float = 1.0, tag_presets: bool = False
) -> ExportSceneModel:
    settings = settings_from_events(scene.events)
    declared = scene.declarations.materials if scene.declarations is not None else None
    materials = resolve_materials(scene.tags, settings.raytracer, declared, tag_presets or declared is not None)
    if camera is None:
        camera = settings.view.camera()
        if not settings.has_view and len(scene):
            x = scene.xform
            lo = (x[:, :, 3] + np.minimum(x[:, :, :3], 0).sum(axis=2)).min(axis=0)
            hi = (x[:, :, 3] + np.maximum(x[:, :, :3], 0).sum(axis=2)).max(axis=0)
            camera = framed(camera, lo, hi, 4 / 3)
    return ExportSceneModel(camera, settings.background, materials, up, unit_scale)
