"""False-colour previews of AOVs for the Render view's channel selector (docs/09 §6, §9).

Every preview is display-linear RGB in [0, 1] (run it through the 'standard' view transform).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .aovs import Aovs

CHANNELS = ("beauty", "albedo", "normal", "depth", "alpha", "instance", "material", "samples")
GOLDEN = 0.618033988749895


def _gray(v: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(v, 0.0, 1.0)[..., None], 3, axis=-1).astype(np.float32)


def depth_preview(depth: np.ndarray) -> np.ndarray:
    """Near = bright, far = dark, background black; normalised to the visible depth range."""
    finite = np.isfinite(depth)
    if not finite.any():
        return _gray(np.zeros(depth.shape, np.float32))
    lo, hi = float(depth[finite].min()), float(depth[finite].max())
    near = 1.0 - (depth - lo) / max(hi - lo, 1e-6)
    return _gray(np.where(finite, 0.15 + 0.85 * near, 0.0))


def id_preview(ids: np.ndarray) -> np.ndarray:
    """A stable, well-separated hue per id (golden-ratio hue steps); -1 (background) is black."""
    hue = (ids.astype(np.float64) * GOLDEN) % 1.0
    k = (np.array([5.0, 3.0, 1.0]) + hue[..., None] * 6.0) % 6.0
    rgb = 0.85 - 0.6 * np.clip(np.minimum(k, 4.0 - k), 0.0, 1.0)
    return np.where((ids >= 0)[..., None], rgb, 0.0).astype(np.float32)


PREVIEWS: dict[str, Callable[[Aovs], np.ndarray]] = {
    "albedo": lambda a: np.clip(a.albedo, 0.0, 1.0),
    "normal": lambda a: np.where((a.alpha > 0)[..., None], a.normal * 0.5 + 0.5, 0.0).astype(np.float32),
    "depth": lambda a: depth_preview(a.depth),
    "alpha": lambda a: _gray(a.alpha),
    "instance": lambda a: id_preview(a.instance),
    "material": lambda a: id_preview(a.material),
}


def heat_preview(values: np.ndarray) -> np.ndarray:
    """A heat ramp (black → blue → red → yellow → white) over 0 … max (adaptive sample map)."""
    t = values.astype(np.float32) / max(float(values.max()), 1.0)
    stops = np.array([[0, 0, 0], [0.1, 0.2, 0.8], [0.9, 0.1, 0.1], [1, 0.9, 0.1], [1, 1, 1]], np.float32)
    at = np.clip(t, 0.0, 1.0) * (len(stops) - 1)
    lo = np.minimum(at.astype(np.int64), len(stops) - 2)
    frac = (at - lo)[..., None]
    ramp: np.ndarray = (stops[lo] * (1 - frac) + stops[lo + 1] * frac).astype(np.float32)
    return ramp


def channel_preview(channel: str, aovs: Aovs | None, sample_map: np.ndarray | None) -> np.ndarray | None:
    """The display-linear preview of a non-beauty channel, or None when the render does not have it."""
    if channel == "samples":
        return heat_preview(sample_map) if sample_map is not None else None
    return PREVIEWS[channel](aovs) if aovs is not None and channel in PREVIEWS else None
