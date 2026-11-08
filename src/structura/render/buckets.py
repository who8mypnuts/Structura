"""Bucket orders for the tiled sampler (docs/09 §5.2, Sunflow's BucketOrder family): the image is cut into
square buckets which are rendered one at a time in the chosen order."""

from __future__ import annotations

import math

import numpy as np

Rect = tuple[int, int, int, int]


def hilbert_index(n: int, x: int, y: int) -> int:
    """Position of cell (x, y) along the Hilbert curve filling an n×n grid (n a power of two)."""
    d, s = 0, n // 2
    while s > 0:
        rx, ry = int(x & s > 0), int(y & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        s //= 2
    return d


def _keys(cols: int, rows: int, order: str, seed: int) -> list[float]:
    cells = [(i, j) for j in range(rows) for i in range(cols)]
    if order == "rows":
        return [j * cols + i for i, j in cells]
    if order == "columns":
        return [i * rows + j for i, j in cells]
    if order == "diagonal":
        return [(i + j) * (cols + rows) + i for i, j in cells]
    if order == "spiral":  # outward from the centre, ring by ring, clockwise inside a ring
        cx, cy = (cols - 1) / 2, (rows - 1) / 2
        return [max(abs(i - cx), abs(j - cy)) * 10 + math.atan2(j - cy, i - cx) / math.tau + 0.5 for i, j in cells]
    if order == "random":
        return list(np.random.default_rng(seed).permutation(len(cells)).astype(float))
    n = 1 << max(0, (max(cols, rows) - 1).bit_length())
    return [float(hilbert_index(n, i, j)) for i, j in cells]


def buckets(width: int, height: int, size: int, order: str = "hilbert", seed: int = 0) -> list[Rect]:
    """The buckets covering a width × height image, in ``order`` (hilbert, spiral, rows, columns, diagonal,
    random); edge buckets are cut to the image."""
    size = max(1, size)
    cols, rows = -(-width // size), -(-height // size)
    keys = _keys(cols, rows, order, seed)
    cells = sorted(range(cols * rows), key=lambda k: keys[k])
    out = []
    for k in cells:
        i, j = k % cols, k // cols
        out.append((i * size, j * size, min(width, (i + 1) * size), min(height, (j + 1) * size)))
    return out
