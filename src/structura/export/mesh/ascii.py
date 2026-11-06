"""Fast ASCII number formatting for text mesh formats (OBJ): Numba writes the digits straight into a byte
buffer, about 20× faster than Python's '%' formatting on millions of vertices (docs/15 §8).

Floats are written in fixed point with at most ``decimals`` decimals and no trailing zeros ('1.5', '-0.25',
'0'); values beyond ±9e12 are clamped. Integers are written plainly.
"""

from __future__ import annotations

import numpy as np

from ...core.jit import host_kernel

MAX_INT = 9_000_000_000_000


@host_kernel
def _digits(out: np.ndarray, at: int, value: int) -> int:
    """Write a non-negative integer at ``at``; returns the position after it."""
    if value == 0:
        out[at] = 48
        return at + 1
    start = at
    while value > 0:
        out[at] = 48 + value % 10
        value //= 10
        at += 1
    end = at - 1
    while start < end:  # the digits came out least significant first
        out[start], out[end] = out[end], out[start]
        start += 1
        end -= 1
    return at


@host_kernel
def _float(out: np.ndarray, at: int, x: float, decimals: int) -> int:
    if not np.isfinite(x):
        x = 0.0
    scale = 10**decimals
    scaled = min(int(abs(x) * scale + 0.5), MAX_INT * scale)
    if scaled == 0:
        out[at] = 48
        return at + 1
    if x < 0:
        out[at] = 45
        at += 1
    at = _digits(out, at, scaled // scale)
    frac = scaled % scale
    if frac == 0:
        return at
    out[at] = 46
    at += 1
    width = decimals
    while frac % 10 == 0:  # trim trailing zeros
        frac //= 10
        width -= 1
    for k in range(width - 1, -1, -1):
        out[at + k] = 48 + frac % 10
        frac //= 10
    return at + width


@host_kernel
def _float_rows(prefix: np.ndarray, data: np.ndarray, decimals: np.ndarray) -> np.ndarray:
    rows, cols = data.shape
    out = np.empty(rows * (len(prefix) + 1 + cols * 32), np.uint8)
    at = 0
    for r in range(rows):
        for c in range(len(prefix)):
            out[at + c] = prefix[c]
        at += len(prefix)
        for c in range(cols):
            out[at] = 32
            at = _float(out, at + 1, data[r, c], decimals[c])
        out[at] = 10
        at += 1
    return out[:at]


@host_kernel
def _face_rows(indices: np.ndarray, base: int, doubled: bool) -> np.ndarray:
    rows, cols = indices.shape
    out = np.empty(rows * (2 + cols * 42), np.uint8)
    at = 0
    for r in range(rows):
        out[at] = 102  # 'f'
        at += 1
        for c in range(cols):
            out[at] = 32
            value = indices[r, c] + base
            at = _digits(out, at + 1, value)
            if doubled:  # 'v//vn' with the same index
                out[at] = 47
                out[at + 1] = 47
                at = _digits(out, at + 2, value)
        out[at] = 10
        at += 1
    return out[:at]


def float_rows(prefix: str, data: np.ndarray, decimals: tuple[int, ...]) -> bytes:
    """'prefix x y z …\\n' per row."""
    if not len(data):
        return b""
    head = np.frombuffer(prefix.encode("ascii"), np.uint8)
    values = np.ascontiguousarray(data, np.float64)
    return bytes(_float_rows(head, values, np.asarray(decimals, np.int64)))


def face_rows(indices: np.ndarray, base: int, with_normals: bool) -> bytes:
    """'f a b c\\n' (or 'f a//a b//b c//c\\n') per triangle, 1-based from ``base``."""
    if not len(indices):
        return b""
    return bytes(_face_rows(np.ascontiguousarray(indices, np.int64), base + 1, with_normals))
