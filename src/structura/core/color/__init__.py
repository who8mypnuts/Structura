"""Colour handling: legacy-exact QColor semantics, HSV (Structure Synth), sRGB <-> linear."""

from .hsv import hsv_to_rgb
from .qcolor_compat import Rgba16, hsv_ints, parse_color
from .srgb import linear_to_srgb, srgb_to_linear, srgb_to_linear_16
from .values import RGB, linear_of, rgb_of

__all__ = [
    "RGB",
    "Rgba16",
    "hsv_ints",
    "hsv_to_rgb",
    "linear_of",
    "linear_to_srgb",
    "parse_color",
    "rgb_of",
    "srgb_to_linear",
    "srgb_to_linear_16",
]
