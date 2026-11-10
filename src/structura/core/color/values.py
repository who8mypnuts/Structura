"""Colours as scripts and settings write them — a QColor name or hex form ('#fa0', 'orange'), or an (r, g, b)
tuple of 0..1 — read once, here, for every consumer (v2 blocks, lights, environments, fog, ground)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .qcolor_compat import MAX16, parse_color
from .srgb import srgb_to_linear

RGB = tuple[float, float, float]


def _channels(value: Any) -> np.ndarray | None:
    """float32 sRGB channels of ``value`` (same arithmetic for names, hex and tuples), or None."""
    if isinstance(value, tuple | list) and len(value) == 3:
        try:
            return np.asarray([float(c) for c in value], np.float32)
        except (TypeError, ValueError):
            return None
    colour = parse_color(str(value)) if value is not None else None
    if colour is None:
        return None
    return np.array([colour.r, colour.g, colour.b], np.float32) / np.float32(MAX16)


def rgb_of(value: Any) -> RGB | None:
    """The sRGB colour of ``value`` as floats in 0..1, or None when it is not a colour."""
    if isinstance(value, tuple | list) and len(value) == 3:
        try:
            r, g, b = (float(c) for c in value)
        except (TypeError, ValueError):
            return None
        return (r, g, b)
    colour = parse_color(str(value)) if value is not None else None
    return None if colour is None else (colour.r / MAX16, colour.g / MAX16, colour.b / MAX16)


def linear_of(value: Any, default: RGB) -> RGB:
    """The linear-light colour of ``value`` (sRGB decoded), or ``default`` when it is not a colour."""
    channels = _channels(value)
    if channels is None:
        return default
    r, g, b = (float(c) for c in srgb_to_linear(channels))
    return (r, g, b)
