"""Emissive geometry as lights (docs/10 §4): every primitive with an emissive material becomes an emitter
record, chosen for next-event estimation in proportion to its power (luminance × area).

Records 'emit_f' (EMIT_F floats; layout below, shared with render/kernels/emitters.py):
  [0] kind (0 sphere, 1 box, 2 triangle)   [1] primitive   [2:5] emitted radiance (linear)
  [5] total area   [6] probability of choosing this record
  sphere: [8:11] centre, [11] radius
  box:    [8:11] corner, [11:14] [14:17] [17:20] edge vectors a, b, c (the transformed unit cube)
  triangle: [8:11] p0, [11:14] e1, [14:17] e2
'prim_emit' maps every primitive to its record (NO_EMITTER when it does not emit); 'emit_cdf' is the
selection CDF (E + 1 entries)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .kernels import layout as lay
from .kernels.scene import RK_BOX, RK_SPHERE, RK_TRIANGLE
from .pack import PackedScene

EMIT_F, NO_EMITTER = lay.EMIT_F, lay.NO_EMITTER
E_KIND, E_PRIM, E_RADIANCE, E_AREA, E_SELECT, E_GEO = (
    lay.E_KIND,
    lay.E_PRIM,
    lay.E_RADIANCE,
    lay.E_AREA,
    lay.E_SELECT,
    lay.E_GEO,
)
KINDS = {RK_SPHERE: 0, RK_BOX: 1, RK_TRIANGLE: 2}


@dataclass(frozen=True)
class Emitters:
    emit_f: np.ndarray  # float32[E, EMIT_F]
    emit_cdf: np.ndarray  # float32[E + 1]
    prim_emit: np.ndarray  # uint32[P]

    def __len__(self) -> int:
        return int(self.emit_f.shape[0])


def _radiance(packed: PackedScene, mat_f: np.ndarray) -> np.ndarray:
    """Emitted radiance of every primitive, as surface_at computes it per hit."""
    m = mat_f[packed.prim_u[:, 1]]
    state = packed.prim_f[:, 12:15]
    mix = m[:, lay.M_EMISSION_STATE : lay.M_EMISSION_STATE + 1]
    radiance: np.ndarray = m[:, lay.M_EMISSION : lay.M_EMISSION + 3] * ((1 - mix) + state * mix)
    return radiance


def _box_geometry(xform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    edges = xform[:, :, :3].transpose(0, 2, 1)  # (N, 3 edges, xyz)
    a, b, c = edges[:, 0], edges[:, 1], edges[:, 2]
    area = 2 * (np.linalg.norm(np.cross(b, c), axis=1) + np.linalg.norm(np.cross(c, a), axis=1)
                + np.linalg.norm(np.cross(a, b), axis=1))  # fmt: skip
    return np.concatenate([xform[:, :, 3], a, b, c], axis=1), area


def _geometry(packed: PackedScene, kind: int, prims: np.ndarray, xform: np.ndarray) -> tuple[np.ndarray, ...]:
    if kind == RK_SPHERE:
        radius = packed.prim_f[prims, 19]
        return np.concatenate([packed.prim_f[prims, 16:19], radius[:, None]], axis=1), 4 * np.pi * radius**2
    if kind == RK_BOX:
        return _box_geometry(xform[packed.prim_u[prims, 2]])
    corners = packed.tri_f[packed.prim_u[prims, 3]].reshape(-1, 3, 3)
    e1, e2 = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    return np.concatenate([corners[:, 0], e1, e2], axis=1), 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)


def pack_emitters(packed: PackedScene, mat_f: np.ndarray, xform: np.ndarray) -> Emitters:
    """``xform``: the SceneIR instance matrices (boxes are rebuilt from them)."""
    radiance = _radiance(packed, mat_f) if len(packed) else np.zeros((0, 3), np.float32)
    luminance = radiance @ np.array([0.2126, 0.7152, 0.0722])
    records, prim_emit = [], np.full(len(packed), NO_EMITTER, np.uint32)
    for rk, kind in KINDS.items():
        prims = np.nonzero((packed.prim_u[:, 0] == rk) & (luminance > 0))[0]
        if not len(prims):
            continue
        geometry, area = _geometry(packed, rk, prims, xform)
        r = np.zeros((len(prims), EMIT_F), np.float32)
        r[:, E_KIND], r[:, E_PRIM], r[:, E_RADIANCE : E_RADIANCE + 3] = kind, prims, radiance[prims]
        r[:, E_AREA], r[:, E_GEO : E_GEO + geometry.shape[1]] = area, geometry
        records.append(r)
    if not records:
        return Emitters(np.zeros((0, EMIT_F), np.float32), np.zeros(1, np.float32), prim_emit)
    emit_f = np.concatenate(records)
    power = emit_f[:, E_AREA] * (emit_f[:, E_RADIANCE : E_RADIANCE + 3] @ np.array([0.2126, 0.7152, 0.0722]))
    emit_f[:, E_SELECT] = power / power.sum()
    prim_emit[emit_f[:, E_PRIM].astype(np.int64)] = np.arange(len(emit_f), dtype=np.uint32)
    cdf = np.concatenate([[0.0], np.cumsum(emit_f[:, E_SELECT])]).astype(np.float32)
    cdf[-1] = 1.0
    return Emitters(emit_f, cdf, prim_emit)
