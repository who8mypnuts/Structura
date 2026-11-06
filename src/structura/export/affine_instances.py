"""Unit prototypes placed by full affine matrices (docs/15 §2.2): for formats whose instances take a 3×4 matrix
(3MF components, POV-Ray, Sunflow, Mitsuba). Shear needs no special case: the matrix carries it.

Every prototype lives in the unit cube like the SceneIR primitive (spheres are placed by centre and radius,
because a Structure Synth sphere is always round). Kinds without a prototype are left to the caller to bake.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.geometry.tessellate import LOD
from ..core.geometry.unit_shapes import Mesh, unit_box, unit_sphere
from ..core.geometry.v2_shapes import unit_shape
from ..core.scene.ir import PrimitiveKind as K
from .base import ExportJob

AFFINE_KINDS = (K.BOX, K.SPHERE, K.ELLIPSOID, K.CYLINDER, K.CONE, K.TORUS)
PARAM_KINDS = (K.CONE, K.TORUS)


@dataclass(frozen=True)
class Prototype:
    key: str  # 'box', 'sphere', 'cone-0.5' …: unique per distinct shape
    kind: K
    param: float
    mesh: Mesh


@dataclass(frozen=True)
class AffineGroup:
    proto: Prototype
    rows: np.ndarray  # int64[N] SceneIR rows
    matrices: np.ndarray  # float32[N, 3, 4]: unit cube → output axes and units


def sphere_affines(xform: np.ndarray) -> np.ndarray:
    """The unit-cube sphere onto each round sphere: [2r·I | centre − r]."""
    centre = xform[:, :, 3] + 0.5 * xform[:, :, :3].sum(axis=2)
    r = np.linalg.norm(0.5 * xform[:, :, 2], axis=1)
    linear = np.eye(3, dtype=np.float32)[None] * (2 * r)[:, None, None]
    return np.concatenate([linear, (centre - r[:, None])[:, :, None]], axis=2).astype(np.float32)


def _prototype(kind: K, param: float, lod: str) -> Prototype:
    rings, segments = LOD[lod]
    if kind == K.BOX:
        mesh = unit_box()
    elif kind == K.SPHERE:
        mesh = unit_sphere(rings, segments)
    else:
        mesh = unit_shape(kind, param, segments)
    key = kind.name.lower() + (f"-{param:g}" if kind in PARAM_KINDS else "")
    return Prototype(key, kind, param, mesh)


def affine_groups(job: ExportJob, lod: str = "medium") -> tuple[list[AffineGroup], np.ndarray]:
    """(groups, covered): one group per distinct prototype; ``covered`` marks the rows they place."""
    scene, groups = job.scene, []
    covered = np.zeros(len(scene), bool)
    for kind in AFFINE_KINDS:
        rows_all = np.nonzero(scene.kind == kind)[0]
        params = scene.params(rows_all) if kind in PARAM_KINDS else np.zeros(len(rows_all), np.float32)
        for value in np.unique(params):
            rows = rows_all[params == value]
            world = sphere_affines(scene.xform[rows]) if kind == K.SPHERE else scene.xform[rows]
            groups.append(AffineGroup(_prototype(kind, float(value), lod), rows, job.model.xforms(world)))
            covered[rows] = True
    return groups, covered
