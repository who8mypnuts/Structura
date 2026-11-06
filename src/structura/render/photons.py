"""Caustic photon map, host side (docs/10 §2.5): trace the photons on the render's device, keep the stored
ones, and pack them into a hash grid the render kernel gathers from (layout in kernels/layout.py)."""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np

from ..compute.base import Backend, Launch
from ..kernels.skl import ir
from ..kernels.skl.frontend import compile_module
from .kernels import layout as lay
from .kernels.photons import CELL_OFFSET, photon_pass

RADIUS_FRACTION = 0.006  # default gather radius, × the scene's bounding radius


@cache
def photon_module() -> ir.Module:
    return compile_module([photon_pass])


def _hash(x: np.ndarray) -> np.ndarray:
    """kernels/sampling.hash_u32 on uint32 arrays (wrapping arithmetic)."""
    x = x.astype(np.uint32)
    x ^= x >> np.uint32(16)
    x *= np.uint32(0x7FEB352D)
    x ^= x >> np.uint32(15)
    x *= np.uint32(0x846CA68B)
    x ^= x >> np.uint32(16)
    return x


def buckets(positions: np.ndarray, radius: float, table: int) -> np.ndarray:
    """The kernel's photon_bucket of each position's cell (cells are 2·radius wide)."""
    cells = (np.floor(positions / (2.0 * radius)) + CELL_OFFSET).astype(np.uint32)
    with np.errstate(over="ignore"):
        inner = _hash(cells[:, 2] * np.uint32(83492791))
        inner = _hash((cells[:, 1] * np.uint32(19349663)) ^ inner)
        return _hash((cells[:, 0] * np.uint32(73856093)) ^ inner) & np.uint32(table - 1)


def photon_map(photons: np.ndarray, radius: float) -> tuple[np.ndarray, int]:
    """(photon_f buffer, table size) for stored photons (M, PHOTON_F)."""
    table = 1 << max(4, int(np.ceil(np.log2(max(2 * len(photons), 16)))))
    bucket = buckets(photons[:, :3], radius, table) if len(photons) else np.zeros(0, np.uint32)
    order = np.argsort(bucket, kind="stable")
    counts = np.bincount(bucket, minlength=table)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    head = np.stack([starts, counts], axis=1).astype(np.float32).ravel()
    return np.concatenate([head, photons[order].astype(np.float32).ravel()]), table


def trace_photons(args: dict[str, Any], backend: Backend, count: int, seed: int) -> np.ndarray:
    """Stored photons (M, PHOTON_F) from a photon_pass over the render's scene buffers."""
    names = {p for p, _ in Launch(photon_module(), "photon_pass", (1, 1, 1), {}).params()}
    kernel_args = {k: v for k, v in args.items() if k in names}
    kernel_args |= {"photons": np.zeros(count * lay.PHOTON_OUT, np.float32), "count": count, "seed": seed}
    bound = backend.bind(Launch(photon_module(), "photon_pass", (count, 1, 1), kernel_args))
    bound.dispatch()
    raw = bound.read("photons").reshape(count, lay.PHOTON_OUT)
    return raw[raw[:, 9] > 0.5, : lay.PHOTON_F]


def add_photons(args: dict[str, Any], lo: np.ndarray, hi: np.ndarray, count: int, radius: float,
                backend: Backend, seed: int) -> int:  # fmt: skip
    """Switch the render's launch arguments to photon caustics; returns the number of stored photons."""
    cfg = args["cfg"].copy()
    centre, extent = (lo + hi) / 2, max(float(np.linalg.norm(hi - lo)) / 2, 1e-3)
    cfg[lay.PHOTON_CENTRE : lay.PHOTON_CENTRE + 3], cfg[lay.PHOTON_EXTENT] = centre, extent
    cfg[lay.PHOTON_COUNT] = count
    args["cfg"] = cfg
    photons = trace_photons(args, backend, count, seed)
    gather = radius if radius > 0 else RADIUS_FRACTION * extent
    buffer, table = photon_map(photons, gather)
    cfg[lay.PHOTONS_ON], cfg[lay.PHOTON_RADIUS], cfg[lay.PHOTON_TABLE] = 1.0, gather, table
    args["photon_f"] = buffer
    return len(photons)
