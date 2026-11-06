"""sRGB transfer functions — the single place where authored colours become linear (docs/07 §9)."""

from __future__ import annotations

from functools import cache

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


def srgb_to_linear(c: FloatArray) -> FloatArray:
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


@cache
def _lut() -> FloatArray:
    return srgb_to_linear(np.arange(65536, dtype=np.float32) / np.float32(65535))


def srgb_to_linear_16(c: FloatArray) -> FloatArray:
    """srgb_to_linear for colours with 16-bit precision (every authored colour is): a table lookup, ~20× faster
    on large per-vertex arrays. Values are clipped to [0, 1]."""
    index = np.rint(np.clip(np.asarray(c, np.float32), 0.0, 1.0) * np.float32(65535)).astype(np.int32)
    out: FloatArray = _lut()[index]
    return out


def linear_to_srgb(c: FloatArray) -> FloatArray:
    c = np.clip(np.asarray(c, dtype=np.float32), 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055).astype(np.float32)
