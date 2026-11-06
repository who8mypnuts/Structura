"""Affine → TRS decomposition with shear detection (docs/15 §2.2).

Instancing formats (USD PointInstancer, glTF EXT_mesh_gpu_instancing, Blender instances) store translation,
rotation and per-axis scale only. ``decompose`` writes L = R · diag(s) with R a proper rotation; instances
whose columns are not orthogonal (Structure Synth's 'matrix', or non-uniform scale followed by rotation)
carry a shear residual and must be baked or exported with a full matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SHEAR_TOLERANCE = 1e-5


@dataclass(frozen=True)
class TRS:
    translation: np.ndarray  # float32[N, 3]
    rotation: np.ndarray  # float32[N, 4] quaternions (x, y, z, w)
    scale: np.ndarray  # float32[N, 3] (negative x for mirrored instances)
    shear: np.ndarray  # float32[N] relative residual ‖RᵀR − I‖

    def representable(self, tolerance: float = SHEAR_TOLERANCE) -> np.ndarray:
        return self.shear <= tolerance


def quaternions(r: np.ndarray) -> np.ndarray:
    """(N,3,3) rotation matrices → (N,4) unit quaternions (x, y, z, w), branch-free (Shepperd)."""
    m = r.astype(np.float64)
    w = np.sqrt(np.maximum(0.0, 1.0 + m[:, 0, 0] + m[:, 1, 1] + m[:, 2, 2])) / 2
    x = np.sqrt(np.maximum(0.0, 1.0 + m[:, 0, 0] - m[:, 1, 1] - m[:, 2, 2])) / 2
    y = np.sqrt(np.maximum(0.0, 1.0 - m[:, 0, 0] + m[:, 1, 1] - m[:, 2, 2])) / 2
    z = np.sqrt(np.maximum(0.0, 1.0 - m[:, 0, 0] - m[:, 1, 1] + m[:, 2, 2])) / 2
    x = np.copysign(x, m[:, 2, 1] - m[:, 1, 2])
    y = np.copysign(y, m[:, 0, 2] - m[:, 2, 0])
    z = np.copysign(z, m[:, 1, 0] - m[:, 0, 1])
    q = np.stack([x, y, z, w], axis=1)
    unit: np.ndarray = (q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-30)).astype(np.float32)
    return unit


def decompose(xform: np.ndarray) -> TRS:
    """(N,3,4) affines [L | t] → TRS (scale along the instance's own axes)."""
    linear = xform[:, :, :3].astype(np.float64)
    scale = np.linalg.norm(linear, axis=1)  # column lengths
    mirrored = np.linalg.det(linear) < 0
    scale[mirrored, 0] *= -1.0
    safe = np.where(np.abs(scale) > 1e-30, scale, 1.0)
    r = linear / safe[:, None, :]
    gram = np.einsum("nki,nkj->nij", r, r)
    shear = np.linalg.norm(gram - np.eye(3), axis=(1, 2))
    flat = (np.abs(scale) <= 1e-30).any(axis=1)
    r[flat] = np.eye(3)  # singular instances: any rotation represents them
    return TRS(
        xform[:, :, 3].astype(np.float32),
        quaternions(r),
        scale.astype(np.float32),
        np.where(flat, 0.0, shear).astype(np.float32),
    )


def compose(trs: TRS) -> np.ndarray:
    """Inverse of decompose for representable instances: (N,3,4)."""
    x, y, z, w = (trs.rotation[:, k].astype(np.float64) for k in range(4))
    r = np.stack(
        [
            np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], axis=1),
            np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], axis=1),
            np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], axis=1),
        ],
        axis=1,
    )
    linear = r * trs.scale[:, None, :].astype(np.float64)
    return np.concatenate([linear, trs.translation[:, :, None]], axis=2).astype(np.float32)
