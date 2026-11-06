"""Float32 helpers for the builder kernel (legacy single-precision arithmetic order)."""

from __future__ import annotations

import math

import numpy as np

from structura.core.jit import kernel

F0 = np.float32(0.0)
F1 = np.float32(1.0)
F60 = np.float32(60.0)
F360 = np.float32(360.0)


@kernel
def _row(f: np.ndarray, j: int, off: int, i: int, x: np.float32, y: np.float32, z: np.float32) -> np.float32:
    acc = F0
    acc = acc + f[j, off + i * 4] * x
    acc = acc + f[j, off + i * 4 + 1] * y
    acc = acc + f[j, off + i * 4 + 2] * z
    return acc + f[j, off + i * 4 + 3]


@kernel
def mat_vec(
    f: np.ndarray, j: int, off: int, x: np.float32, y: np.float32, z: np.float32
) -> tuple[np.float32, np.float32, np.float32]:
    """M · (x, y, z, 1) for the 4×4 row-major matrix stored at f[j, off:off+16] (legacy accumulation order)."""
    return _row(f, j, off, 0, x, y, z), _row(f, j, off, 1, x, y, z), _row(f, j, off, 2, x, y, z)


@kernel
def hsv_to_rgb32(h: np.float32, s: np.float32, v: np.float32) -> tuple[np.float32, np.float32, np.float32]:
    if h >= F360:
        h = h - F360
    q60 = h / F60
    sector = int(q60)  # truncation toward zero, as a C cast
    i = sector % 6 if sector >= 0 else -((-sector) % 6)
    f = q60 - np.float32(sector)  # float arithmetic, stored in a double in 1.5
    p = v * (F1 - s)  # a float expression
    fd, sd, vd = np.float64(f), np.float64(s), np.float64(v)
    q = np.float32(vd * (1.0 - fd * sd))  # double expressions (f is a double), rounded once to float
    t = np.float32(vd * (1.0 - (1.0 - fd) * sd))
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    return v, p, q


@kernel
def _qround(x: float) -> int:
    return int(x + 0.5) if x >= 0.0 else int(x - 0.5)


@kernel
def _fuzzy(p: float, q: float) -> bool:
    return abs(p - q) * 1e12 <= min(abs(p), abs(q))


@kernel
def rgb8_to_hsv_ints(r8: int, g8: int, b8: int) -> tuple[int, int, int]:
    """QColor(r,g,b).toHsv() → (hue, saturation, value) integers (see core.color.qcolor_compat)."""
    r, g, b = r8 * 257 / 65535.0, g8 * 257 / 65535.0, b8 * 257 / 65535.0
    mx, mn = max(r, max(g, b)), min(r, min(g, b))
    delta = mx - mn
    value = _qround(mx * 65535.0)
    if abs(delta) <= 1e-12:
        return -1, 0, (value - (value >> 8) + 0x80) >> 8
    sat = _qround(delta / mx * 65535.0)
    if _fuzzy(r, mx):
        hue = (g - b) / delta
    elif _fuzzy(g, mx):
        hue = 2.0 + (b - r) / delta
    else:
        hue = 4.0 + (r - g) / delta
    hue *= 60.0
    if hue < 0.0:
        hue += 360.0
    return _qround(hue * 100.0) // 100, (sat - (sat >> 8) + 0x80) >> 8, (value - (value >> 8) + 0x80) >> 8


@kernel
def length32(x: np.float32, y: np.float32, z: np.float32) -> np.float32:
    return np.float32(math.sqrt(x * x + y * y + z * z))
