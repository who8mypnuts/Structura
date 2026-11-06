"""Structural invariants of the binned-SAH BVH (docs/09 §3.2)."""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from structura.render.bvh import Bvh, build_bvh


def _boxes(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    lo = rng.uniform(-10, 10, (n, 3)).astype(np.float32)
    return lo, lo + rng.uniform(0, 1, (n, 3)).astype(np.float32)


def _walk(bvh: Bvh) -> list[tuple[int, int]]:
    """Leaves as (first, count); asserts every child lies inside its parent."""
    leaves, stack = [], [0]
    while stack:
        node = stack.pop()
        a, count = (int(v) for v in bvh.node_u[node])
        if count:
            leaves.append((a, count))
            continue
        for child in (a, a + 1):
            assert np.all(bvh.node_f[child, :3] >= bvh.node_f[node, :3])
            assert np.all(bvh.node_f[child, 3:] <= bvh.node_f[node, 3:])
            stack.append(child)
    return leaves


@settings(max_examples=25, deadline=None)
@given(st.integers(1, 400), st.integers(0, 2**31))
def test_every_primitive_is_in_exactly_one_leaf_inside_its_bounds(n: int, seed: int) -> None:
    lo, hi = _boxes(n, seed)
    bvh = build_bvh(lo, hi)
    assert sorted(bvh.order.tolist()) == list(range(n))
    seen = []
    for first, count in _walk(bvh):
        node = next(i for i in range(bvh.nodes) if tuple(bvh.node_u[i]) == (first, count))
        for p in bvh.order[first : first + count]:
            assert np.all(lo[p] >= bvh.node_f[node, :3]) and np.all(hi[p] <= bvh.node_f[node, 3:])
            seen.append(int(p))
    assert sorted(seen) == list(range(n))


def test_identical_boxes_still_terminate() -> None:
    lo = np.zeros((1000, 3), np.float32)
    bvh = build_bvh(lo, lo + 1)
    assert sum(c for _, c in _walk(bvh)) == 1000


def test_empty_scene_has_one_empty_leaf() -> None:
    bvh = build_bvh(np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32))
    assert bvh.nodes == 1 and len(bvh.order) == 0
