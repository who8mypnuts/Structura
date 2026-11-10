"""The optional ground under a render (docs/10 §2.3): a plain diffuse plane or a shadow catcher.

The ground is a very large, thin box appended to the packed scene, with its own material, so the BVH,
lights, AOVs and every integrator handle it like any other primitive. With the shadow-catcher model, camera
rays that hit it see the background, darkened by the fraction of light the scene blocks (path integrator).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ..core.color import srgb_to_linear
from ..core.scene.material import Material, MaterialModel
from ..core.scene.material_library import MaterialTable
from .kernels.scene import PRIM_F, PRIM_U, RK_BOX
from .pack import PackedScene, box_bounds, inverse_rows

MODES = ("off", "plane", "catcher")
SIZE, THICKNESS = 1000.0, 1e-3  # × the scene extent


@dataclass(frozen=True)
class Ground:
    catcher: bool = False
    color: tuple[float, float, float] = (0.8, 0.8, 0.8)  # sRGB
    offset: float = 0.0  # how far below the scene's lowest point (world units)

    def material(self) -> Material:
        model = MaterialModel.SHADOW_CATCHER if self.catcher else MaterialModel.PRINCIPLED
        return Material(name="ground", model=model, roughness=0.9, specular=0.3)


def ground_xform(lo: np.ndarray, hi: np.ndarray, offset: float) -> np.ndarray:
    """(1, 3, 4) object→world matrix of the ground box: its top face at the scene's lowest y − offset."""
    extent = max(float((hi - lo).max()), 1e-3)
    size, thickness = SIZE * extent, THICKNESS * extent
    cx, cz = float(lo[0] + hi[0]) / 2, float(lo[2] + hi[2]) / 2
    top = float(lo[1]) - offset
    return np.array([[[2 * size, 0, 0, cx - size], [0, thickness, 0, top - thickness],
                      [0, 0, 2 * size, cz - size]]], np.float32)  # fmt: skip


def with_ground(
    packed: PackedScene, materials: MaterialTable, ground: Ground, row: int, lo: np.ndarray, hi: np.ndarray
) -> tuple[PackedScene, MaterialTable]:
    """``packed`` plus the ground primitive (instance ``row``), ``materials`` plus its material."""
    existing = materials.materials or (Material(),)  # an empty table means "everything uses the default"
    xform = ground_xform(lo, hi, ground.offset)
    f = np.zeros((1, PRIM_F), np.float32)
    u = np.zeros((1, PRIM_U), np.uint32)
    f[0, :12] = inverse_rows(xform)[0]
    f[0, 12:15], f[0, 15] = srgb_to_linear(np.asarray(ground.color, np.float32)), 1.0
    u[0, 0], u[0, 1], u[0, 2] = RK_BOX, len(existing), row
    g_lo, g_hi = box_bounds(xform)
    grown = PackedScene(np.concatenate([packed.prim_f, f]), np.concatenate([packed.prim_u, u]), packed.tri_f,
                        np.concatenate([packed.lo, g_lo]), np.concatenate([packed.hi, g_hi]))  # fmt: skip
    return grown, replace(materials, materials=(*existing, ground.material()))
