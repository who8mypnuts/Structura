"""World-space triangles of 'mesh' sweeps and 'triangle[…]' primitives (shared by renderers and exporters)."""

from __future__ import annotations

import numpy as np

from ..scene.ir import PrimitiveKind as K
from ..scene.ir import SceneIR

SWEEP_TRIANGLES = 12


def sweep_triangles(scene: SceneIR, rows: np.ndarray) -> np.ndarray:
    """float32[N·12, 9]: a closed quad tube from each sweep's previous frame to its current one."""
    aux = scene.aux_data[scene.aux[rows]]
    o, v1, v2 = aux[:, 0:3], aux[:, 3:6], aux[:, 6:9]
    x = scene.xform[rows]
    e, u1, u2 = x[:, :, 3], x[:, :, 0], x[:, :, 1]
    quads = [
        (o, o + v2, o + v2 + v1, o + v1),
        (e, e + u1, e + u2 + u1, e + u2),
        (o, e, e + u2, o + v2),
        (o + v1, o + v2 + v1, e + u2 + u1, e + u1),
        (o, o + v1, e + u1, e),
        (o + v2, e + u2, e + u2 + u1, o + v1 + v2),
    ]
    tris = [np.stack(t, axis=1) for q in quads for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
    return np.stack(tris, axis=1).reshape(-1, 9).astype(np.float32)  # grouped per sweep


def scene_triangles(scene: SceneIR) -> tuple[np.ndarray, np.ndarray]:
    """(float32[T, 9] corners, int64[T] owning SceneIR row) for every mesh sweep and triangle primitive."""
    meshes = np.nonzero(scene.kind == K.MESH)[0]
    singles = np.nonzero(scene.kind == K.TRIANGLE)[0]
    owners = np.concatenate([np.repeat(meshes, SWEEP_TRIANGLES), singles]).astype(np.int64)
    if not owners.size:
        return np.zeros((0, 9), np.float32), owners
    corners = np.concatenate([sweep_triangles(scene, meshes), scene.aux_data[scene.aux[singles], :9]])
    return corners.astype(np.float32), owners
