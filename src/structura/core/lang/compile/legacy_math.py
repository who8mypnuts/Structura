"""Float32 transformation matrices with Structure Synth's conventions (docs/05 §4.2).

All matrices are row-major 4×4 float32 arrays; products accumulate in float32 in index order so compiled
transformations match the legacy single-precision results as closely as possible.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

Mat = NDArray[np.float32]
F32 = np.float32
LEGACY_PI = 3.14159265


def identity() -> Mat:
    return np.eye(4, dtype=np.float32)


def matmul(a: Mat, b: Mat) -> Mat:
    out = np.zeros((4, 4), dtype=np.float32)
    for r in range(4):
        for c in range(4):
            acc = F32(0.0)
            for i in range(4):
                acc = F32(acc + F32(a[r, i] * b[i, c]))
            out[r, c] = acc
    return out


def translation(x: float, y: float, z: float) -> Mat:
    m = identity()
    m[0, 3], m[1, 3], m[2, 3] = F32(x), F32(y), F32(z)
    return m


def about_centre(core: Mat, pivot: tuple[float, float, float]) -> Mat:
    """T(pivot) · core · T(-pivot), associated left to right."""
    px, py, pz = pivot
    return matmul(matmul(translation(px, py, pz), core), translation(-px, -py, -pz))


def rotation(axis: tuple[float, float, float], angle: float) -> Mat:
    a = F32(angle)
    c, s = F32(math.cos(float(a))), F32(math.sin(float(a)))
    omc = F32(F32(1.0) - c)
    x, y, z = (F32(v) for v in axis)
    xs, ys, zs = F32(x * s), F32(y * s), F32(z * s)
    xy, xz, yz = F32(F32(x * y) * omc), F32(F32(x * z) * omc), F32(F32(y * z) * omc)
    m = identity()
    m[0, 0], m[1, 0], m[2, 0] = F32(F32(F32(x * x) * omc) + c), F32(xy + zs), F32(xz - ys)
    m[0, 1], m[1, 1], m[2, 1] = F32(xy - zs), F32(F32(F32(y * y) * omc) + c), F32(yz + xs)
    m[0, 2], m[1, 2], m[2, 2] = F32(xz + ys), F32(yz - xs), F32(F32(F32(z * z) * omc) + c)
    return m


def axis_rotation(axis_index: int, degrees: float) -> Mat:
    radians = degrees * LEGACY_PI / 180.0
    axis = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)][axis_index]
    pivot = [(0.0, 0.5, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.0)][axis_index]
    return about_centre(rotation(axis, radians), pivot)


def scale(x: float, y: float, z: float) -> Mat:
    m = identity()
    m[0, 0], m[1, 1], m[2, 2] = F32(x), F32(y), F32(z)
    return about_centre(m, (0.5, 0.5, 0.5))


def matrix3(values: tuple[float, ...]) -> Mat:
    m = identity()
    m[:3, :3] = np.asarray(values, dtype=np.float32).reshape(3, 3)
    return about_centre(m, (0.5, 0.5, 0.5))


def plane_reflection(nx: float, ny: float, nz: float) -> Mat:
    n = np.array([nx, ny, nz], dtype=np.float32)
    length = F32(math.sqrt(float(F32(F32(n[0] * n[0]) + F32(n[1] * n[1])) + F32(n[2] * n[2]))))
    inv = F32(1.0 / float(length))
    x, y, z = (float(F32(v * inv)) for v in n)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0], m[1, 0], m[2, 0] = 1.0 - 2.0 * x * x, -2.0 * y * x, -2.0 * z * x
    m[0, 1], m[1, 1], m[2, 1] = -2.0 * x * y, 1.0 - 2.0 * y * y, -2.0 * z * y
    m[0, 2], m[1, 2], m[2, 2] = -2.0 * x * z, -2.0 * y * z, 1.0 - 2.0 * z * z
    m[3, 3] = 1.0
    return m
