"""Binned-SAH bounding volume hierarchy over primitive AABBs (docs/09 §3.2), built with Numba.

Node layout (flat ABI): node_f float32[N, 6] = (min xyz, max xyz); node_u uint32[N, 2] = (a, count).
count > 0: leaf holding primitives order[a : a + count].  count == 0: inner node with children a and a + 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.jit import host_kernel

BINS = 16
ALL_AXES_BELOW = 4096  # nodes with more primitives are split along their widest centroid axis only
LEAF_SIZE = 4
STACK = 128


@dataclass(frozen=True)
class Bvh:
    node_f: np.ndarray  # float32[N, 6]
    node_u: np.ndarray  # uint32[N, 2]
    order: np.ndarray  # uint32[P] primitive index per leaf slot

    @property
    def nodes(self) -> int:
        return int(self.node_u.shape[0])


@host_kernel
def _bounds(lo: np.ndarray, hi: np.ndarray, order: np.ndarray, start: int, end: int, out: np.ndarray) -> None:
    for k in range(3):
        out[k], out[3 + k] = np.inf, -np.inf
    for p in range(start, end):
        for k in range(3):
            out[k] = min(out[k], lo[p, k])
            out[3 + k] = max(out[3 + k], hi[p, k])


@host_kernel
def _area(b: np.ndarray) -> float:
    dx, dy, dz = max(b[3] - b[0], 0.0), max(b[4] - b[1], 0.0), max(b[5] - b[2], 0.0)
    return dx * dy + dy * dz + dz * dx


@host_kernel
def _centroid_bounds(geo, order, start, end, cmin, cmax):  # type: ignore[no-untyped-def]
    lo, hi = geo
    cmin[:], cmax[:] = np.inf, -np.inf
    for p in range(start, end):
        for k in range(3):
            c = 0.5 * (lo[p, k] + hi[p, k])
            cmin[k], cmax[k] = min(cmin[k], c), max(cmax[k], c)


@host_kernel
def _fill_bins(geo, order, start, end, axis, span, ws):  # type: ignore[no-untyped-def]
    lo, hi = geo
    c0, extent = span
    bins_lo, bins_hi, counts, _ = ws
    counts[:] = 0
    bins_lo[:, :], bins_hi[:, :] = np.inf, -np.inf
    for p in range(start, end):
        b = min(BINS - 1, int((0.5 * (lo[p, axis] + hi[p, axis]) - c0) / extent * BINS))
        counts[b] += 1
        for k in range(3):
            bins_lo[b, k] = min(bins_lo[b, k], lo[p, k])
            bins_hi[b, k] = max(bins_hi[b, k], hi[p, k])


@host_kernel
def _grow(box, bins_lo, bins_hi, b):  # type: ignore[no-untyped-def]
    for k in range(3):
        box[k] = min(box[k], bins_lo[b, k])
        box[3 + k] = max(box[3 + k], bins_hi[b, k])


@host_kernel
def _sweep(ws, box):  # type: ignore[no-untyped-def]
    """O(BINS) prefix/suffix SAH sweep over filled bins; returns (best split index, cost)."""
    bins_lo, bins_hi, counts, left_cost = ws
    box[:3], box[3:] = np.inf, -np.inf
    n = 0
    for b in range(BINS - 1):
        n += counts[b]
        _grow(box, bins_lo, bins_hi, b)
        left_cost[b + 1] = n * _area(box) if n > 0 else 0.0
    box[:3], box[3:] = np.inf, -np.inf
    n, best, best_cost = 0, -1, np.inf
    for b in range(BINS - 1, 0, -1):
        n += counts[b]
        _grow(box, bins_lo, bins_hi, b)
        cost = left_cost[b] + (n * _area(box) if n > 0 else 0.0)
        if cost < best_cost:
            best, best_cost = b, cost
    return best, best_cost


@host_kernel
def _best_split(geo, order, start, end, ws):  # type: ignore[no-untyped-def]
    """(axis, split position, cost) of the best binned-SAH split of order[start:end] (axis -1 = none)."""
    cmin, cmax, box = np.empty(3), np.empty(3), np.empty(6)
    _centroid_bounds(geo, order, start, end, cmin, cmax)
    best_axis, best_pos, best_cost = -1, 0.0, np.inf
    widest = 0
    for k in range(1, 3):
        if cmax[k] - cmin[k] > cmax[widest] - cmin[widest]:
            widest = k
    for axis in range(3):
        extent = cmax[axis] - cmin[axis]
        if extent <= 1e-12 or (end - start > ALL_AXES_BELOW and axis != widest):
            continue  # large nodes: bin only the widest centroid axis (3× fewer passes, same quality in practice)
        _fill_bins(geo, order, start, end, axis, (cmin[axis], extent), ws)
        split, cost = _sweep(ws, box)
        if cost < best_cost:
            best_axis, best_pos, best_cost = axis, cmin[axis] + extent * split / BINS, cost
    return best_axis, best_pos, best_cost


@host_kernel
def _swap(geo, order, i, j) -> None:  # type: ignore[no-untyped-def]
    lo, hi = geo
    order[i], order[j] = order[j], order[i]
    for k in range(3):
        lo[i, k], lo[j, k] = lo[j, k], lo[i, k]
        hi[i, k], hi[j, k] = hi[j, k], hi[i, k]


@host_kernel
def _partition(geo, order, start, end, axis, pos) -> int:  # type: ignore[no-untyped-def]
    """Split [start, end) by centroid. The boxes move with ``order``, so every pass reads memory in sequence
    (indirect reads were cache-miss bound: 5× slower at 1M primitives)."""
    lo, hi = geo
    i, j = start, end - 1
    while i <= j:
        if 0.5 * (lo[i, axis] + hi[i, axis]) < pos:
            i += 1
        else:
            _swap(geo, order, i, j)
            j -= 1
    return i


@host_kernel
def _choose_mid(geo, order, start, end, box, ws) -> int:  # type: ignore[no-untyped-def]
    """Partition point for a node, or -1 to make it a leaf."""
    count = end - start
    if count <= LEAF_SIZE:
        return -1
    axis, pos, cost = _best_split(geo, order, start, end, ws)
    mid = _partition(geo, order, start, end, axis, pos) if axis >= 0 else start
    if mid in (start, end):
        return start + count // 2  # degenerate split: divide by count
    if cost >= count * _area(box) and count <= 2 * LEAF_SIZE:
        return -1
    return mid


@host_kernel
def _build(geo, order, node_f, node_u, ws) -> int:  # type: ignore[no-untyped-def]
    """Iterative top-down build; returns the node count."""
    lo, hi = geo
    stack = np.empty((STACK, 3), np.int64)  # (node, start, end)
    stack[0, 0], stack[0, 1], stack[0, 2] = 0, 0, order.shape[0]
    depth, used = 1, 1
    box = np.empty(6)
    while depth > 0:
        depth -= 1
        node, start, end = stack[depth, 0], stack[depth, 1], stack[depth, 2]
        _bounds(lo, hi, order, start, end, box)
        node_f[node, :] = box
        mid = _choose_mid(geo, order, start, end, box, ws)
        if mid < 0:
            node_u[node, 0], node_u[node, 1] = start, end - start
            continue
        left = used
        used += 2
        node_u[node, 0], node_u[node, 1] = left, 0
        stack[depth, 0], stack[depth, 1], stack[depth, 2] = left + 1, mid, end
        stack[depth + 1, 0], stack[depth + 1, 1], stack[depth + 1, 2] = left, start, mid
        depth += 2
    return used


def build_bvh(lo: np.ndarray, hi: np.ndarray) -> Bvh:
    n = len(lo)
    if n == 0:
        return Bvh(np.zeros((1, 6), np.float32), np.zeros((1, 2), np.uint32), np.zeros(0, np.uint32))
    order = np.arange(n, dtype=np.int64)
    node_f = np.zeros((2 * n, 6), np.float32)
    node_u = np.zeros((2 * n, 2), np.int64)
    ws = (np.empty((BINS, 3), np.float32), np.empty((BINS, 3), np.float32), np.zeros(BINS, np.int64), np.zeros(BINS))
    geo = (np.array(lo, np.float32), np.array(hi, np.float32))  # private copies: they are permuted in place
    used = _build(geo, order, node_f, node_u, ws)
    return Bvh(node_f[:used].astype(np.float32), node_u[:used].astype(np.uint32), order.astype(np.uint32))
