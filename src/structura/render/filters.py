"""Pixel reconstruction filters (docs/09 §6), used by *filter importance sampling*: each sample's offset from
the pixel centre is drawn from the filter's |f| (separably in x and y) and weighted by the sign of f, so
wide filters with negative lobes work without splatting into neighbours (no atomics on any backend).

The kernel reads one table, appended to 'cfg' at FILTER_BASE: TABLE + 1 inverse-CDF offsets (pixels)
followed by SIGN_BINS signs of f across [-radius, radius]."""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import cache

import numpy as np

from .kernels import layout as lay

TABLE, SIGN_BINS = lay.FILTER_TABLE, lay.FILTER_SIGNS
Filter = Callable[[np.ndarray], np.ndarray]


def _mitchell(b: float, c: float) -> Filter:
    def f(x: np.ndarray) -> np.ndarray:
        x = np.abs(x)
        near = (12 - 9 * b - 6 * c) * x**3 + (-18 + 12 * b + 6 * c) * x**2 + (6 - 2 * b)
        far = (-b - 6 * c) * x**3 + (6 * b + 30 * c) * x**2 + (-12 * b - 48 * c) * x + (8 * b + 24 * c)
        return np.where(x < 1, near, np.where(x < 2, far, 0.0)) / 6

    return f


def _blackman_harris(radius: float) -> Filter:
    def f(x: np.ndarray) -> np.ndarray:
        t = 2 * math.pi * (x / (2 * radius) + 0.5)
        return 0.35875 - 0.48829 * np.cos(t) + 0.14128 * np.cos(2 * t) - 0.01168 * np.cos(3 * t)

    return f


def _lanczos(a: float) -> Filter:
    return lambda x: np.sinc(x) * np.sinc(x / a)


FILTERS: dict[str, tuple[float, Filter]] = {  # name → (radius in pixels, f)
    "box": (0.5, np.ones_like),
    "triangle": (1.0, lambda x: 1 - np.abs(x)),
    "gaussian": (1.5, lambda x: np.exp(-2 * x * x) - math.exp(-2 * 1.5**2)),
    "blackman-harris": (2.0, _blackman_harris(2.0)),
    "mitchell": (2.0, _mitchell(1 / 3, 1 / 3)),
    "catmull-rom": (2.0, _mitchell(0.0, 0.5)),
    "bspline": (2.0, _mitchell(1.0, 0.0)),
    "lanczos": (3.0, _lanczos(3.0)),
    "sinc": (2.0, np.sinc),  # Sunflow's SincFilter: size 4, unwindowed
}


@cache
def filter_table(name: str) -> tuple[np.ndarray, float]:
    """(table, radius) for the kernel; 'box' keeps the classic uniform jitter (the table is not used)."""
    radius, f = FILTERS[name]
    x = np.linspace(-radius, radius, 4097)
    magnitude = np.abs(f(x))
    cdf = np.concatenate([[0.0], np.cumsum((magnitude[1:] + magnitude[:-1]) / 2)])
    cdf /= cdf[-1]
    inverse = np.interp(np.linspace(0.0, 1.0, TABLE + 1), cdf, x)
    centres = (np.arange(SIGN_BINS) + 0.5) / SIGN_BINS * 2 * radius - radius
    signs = np.where(f(centres) < 0, -1.0, 1.0)
    return np.concatenate([inverse, signs]).astype(np.float32), radius
