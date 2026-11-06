"""Instancing shared by the USD and glTF writers (docs/15 §2.2): boxes whose transform is a TRS and all
spheres, grouped by material, with per-instance translation / rotation / scale in output axes.

Prototypes: the unit box spans [0, 1]³; the unit sphere has centre 0 and radius 1. Sheared boxes are
returned in a mask so the caller bakes them into meshes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...core.geometry.affine import decompose
from ...core.scene.ir import PrimitiveKind as K
from ..base import ExportJob

INSTANCED_KINDS = (K.BOX, K.SPHERE)


@dataclass(frozen=True)
class InstanceGroup:
    kind: K
    material: int
    rows: np.ndarray  # int64[N] SceneIR rows
    translation: np.ndarray  # float32[N, 3]
    rotation: np.ndarray  # float32[N, 4] quaternions (x, y, z, w)
    scale: np.ndarray  # float32[N, 3]


def _trs(job: ExportJob, kind: K, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = job.model.xforms(job.scene.xform[rows])
    if kind == K.BOX:
        trs = decompose(x)
        return trs.translation, trs.rotation, trs.scale
    radius = np.linalg.norm(0.5 * x[:, :, 2], axis=1)
    identity = np.tile(np.array([0, 0, 0, 1], np.float32), (len(rows), 1))
    return x[:, :, 3] + 0.5 * x[:, :, :3].sum(axis=2), identity, np.repeat(radius[:, None], 3, axis=1)


def instance_groups(job: ExportJob) -> tuple[list[InstanceGroup], np.ndarray]:
    """(groups, sheared): one group per (kind, material); ``sheared`` marks box rows to bake instead."""
    scene, table = job.scene, job.model.materials
    mat_of_row = table.by_tag[scene.tag] if len(scene) else np.zeros(0, np.int32)
    sheared = np.zeros(len(scene), bool)
    groups: list[InstanceGroup] = []
    for kind in INSTANCED_KINDS:
        rows_all = np.nonzero(scene.kind == kind)[0]
        if kind == K.BOX and len(rows_all):
            bad = ~decompose(job.model.xforms(scene.xform[rows_all])).representable()
            sheared[rows_all[bad]] = True
            rows_all = rows_all[~bad]
        for m in np.unique(mat_of_row[rows_all]):
            rows = rows_all[mat_of_row[rows_all] == m]
            t, r, s = _trs(job, kind, rows)
            f32 = np.float32
            groups.append(InstanceGroup(kind, int(m), rows, t.astype(f32), r.astype(f32), s.astype(f32)))
    return groups, sheared
