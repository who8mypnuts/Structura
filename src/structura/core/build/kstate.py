"""Kernel: state copies, transformation application and colour-pool draws (docs/05 §4.2–4.4, §6.2).

States are packed rows (see layout.py): ``states.f[j]`` floats (matrix, hsv, alpha, previous frame) and
``states.i[j]`` integers (rule, source, generation, has-previous, seed, material tag, depth slots).
"""

from __future__ import annotations

import numpy as np

from structura.core.jit import kernel

from ..rng.mt19937 import mt_get_int_n
from .kmath import F0, F1, F360, rgb8_to_hsv_ints
from .layout import F_ALPHA, F_HSV, I_MAT

POOL_RANDOM_HUE, POOL_GREY, POOL_RGB, POOL_IMAGE, POOL_LIST = 0, 1, 2, 3, 4
F255 = 255.0


@kernel
def copy_entry(a, i: int, b, j: int) -> None:  # type: ignore[no-untyped-def]
    """b[j] = a[i] (both packed rows)."""
    for k in range(a.f.shape[1]):
        b.f[j, k] = a.f[i, k]
    for k in range(a.i.shape[1]):
        b.i[j, k] = a.i[i, k]


@kernel
def copy_floats(f: np.ndarray, i: int, start: int, j: int, dst_start: int, count: int) -> None:
    for k in range(count):
        f[j, dst_start + k] = f[i, start + k]


@kernel
def draw_pool(tables, pool: int, col_rng: np.ndarray) -> tuple[int, int, int]:  # type: ignore[no-untyped-def]
    kind = tables.pool_kind[pool]
    start, count, width = tables.pool_span[pool, 0], tables.pool_span[pool, 1], tables.pool_span[pool, 2]
    if kind == POOL_RANDOM_HUE:
        return mt_get_int_n(col_rng, 359), 255, 255
    if kind == POOL_GREY:
        return -1, 0, mt_get_int_n(col_rng, 255)
    if kind == POOL_RGB:
        r = mt_get_int_n(col_rng, 255)
        g = mt_get_int_n(col_rng, 255)
        b = mt_get_int_n(col_rng, 255)
        return rgb8_to_hsv_ints(r, g, b)
    if kind == POOL_IMAGE:
        height = count // width
        x = mt_get_int_n(col_rng, width - 1)
        y = mt_get_int_n(col_rng, height - 1)
        row = start + y * width + x
    else:
        row = start + mt_get_int_n(col_rng, count - 1)
    return tables.pool_hsv[row, 0], tables.pool_hsv[row, 1], tables.pool_hsv[row, 2]


@kernel
def _relative_color(tables, x: int, f: np.ndarray, j: int) -> None:  # type: ignore[no-untyped-def]
    h = f[j, F_HSV] + tables.xf_col[x, 0]
    s = min(max(f[j, F_HSV + 1] * tables.xf_col[x, 1], F0), F1)
    v = min(max(f[j, F_HSV + 2] * tables.xf_col[x, 2], F0), F1)
    a = min(max(f[j, F_ALPHA] * tables.xf_col[x, 3], F0), F1)
    while h > F360:
        h = h - F360
    while h < F0:
        h = h + F360
    f[j, F_HSV], f[j, F_HSV + 1], f[j, F_HSV + 2], f[j, F_ALPHA] = h, s, v, a


@kernel
def _blend(tables, x: int, f: np.ndarray, j: int) -> None:  # type: ignore[no-untyped-def]
    k = tables.xf_strength[x]
    t = np.float32(1.0 / np.float32(1.0 + k))
    b0 = np.float32(f[j, F_HSV] + k * tables.xf_blend[x, 0]) * t
    b1 = np.float32(f[j, F_HSV + 1] + k * tables.xf_blend[x, 1]) * t
    b2 = np.float32(f[j, F_HSV + 2] + k * tables.xf_blend[x, 2]) * t
    while b0 < F0:
        b0 = b0 + F360
    while b0 > F360:
        b0 = b0 - F360
    f[j, F_HSV], f[j, F_HSV + 1], f[j, F_HSV + 2] = b0, min(max(b1, F0), F1), min(max(b2, F0), F1)


@kernel
def _matrix(tables, x: int, f: np.ndarray, j: int, tmp: np.ndarray) -> None:  # type: ignore[no-untyped-def]
    """f[j].M ← f[j].M · xf_m[x] (row-major, float32, legacy accumulation order)."""
    xm = tables.xf_m
    for r in range(4):
        for c in range(4):
            acc = F0
            for k in range(4):
                acc = acc + f[j, r * 4 + k] * xm[x, k * 4 + c]
            tmp[r * 4 + c] = acc
    for k in range(16):
        f[j, k] = tmp[k]


@kernel
def apply_xf(tables, x: int, states, j: int, col_rng: np.ndarray, pool: int, tmp: np.ndarray) -> None:  # type: ignore[no-untyped-def]
    """states[j] ← Transformation x applied to states[j] (matrix post-multiplied, then colour, then blend)."""
    f = states.f
    _matrix(tables, x, f, j, tmp)
    if tables.xf_abs[x]:
        if tables.xf_col[x, 0] > 360.0:
            h, s, v = draw_pool(tables, pool, col_rng)
            f[j, F_HSV], f[j, F_HSV + 1], f[j, F_HSV + 2] = np.float32(h), np.float32(s / F255), np.float32(v / F255)
            f[j, F_ALPHA] = F1
        else:
            f[j, F_HSV], f[j, F_HSV + 1], f[j, F_HSV + 2] = (
                tables.xf_col[x, 0],
                tables.xf_col[x, 1],
                tables.xf_col[x, 2],
            )
            f[j, F_ALPHA] = tables.xf_col[x, 3]
    else:
        _relative_color(tables, x, f, j)
    if tables.xf_strength[x] != 0.0:
        _blend(tables, x, f, j)
    if tables.xf_mat[x] >= 0:
        states.i[j, I_MAT] = tables.xf_mat[x]
