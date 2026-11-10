"""Colours as scripts and settings write them — a QColor name or hex form ('#fa0', 'orange'), or an (r, g, b)
tuple of 0..1 — read once, here, for every consumer (v2 blocks, lights, environments, fog, ground)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .qcolor_compat import MAX16, parse_color
from .srgb import srgb_to_linear

RGB = tuple[float, float, float]


def rgb_of(value: Any) -> RGB | None:
    """Reads an sRGB colour.

    Args:
        value: A QColor name or hex form ('#fa0', 'orange'), or three numbers in 0..1.

    Returns:
        (r, g, b) as floats in 0..1, or None when ``value`` is not a colour.
    """
    if isinstance(value, tuple | list) and len(value) == 3:
        try:
            r, g, b = (float(c) for c in value)
        except (TypeError, ValueError):
            return None
        return (r, g, b)
    colour = parse_color(str(value)) if value is not None else None
    return None if colour is None else (colour.r / MAX16, colour.g / MAX16, colour.b / MAX16)


def linear_of(value: Any, default: RGB) -> RGB:
    """Reads a colour as linear light (the sRGB transfer decoded, in float32 like the renderer).

    Args:
        value: Anything ``rgb_of`` reads.
        default: What to return when ``value`` is not a colour.

    Returns:
        The linear (r, g, b), or ``default``.
    """
    srgb = rgb_of(value)
    if srgb is None:
        return default
    r, g, b = (float(c) for c in srgb_to_linear(np.asarray(srgb, np.float32)))
    return (r, g, b)
