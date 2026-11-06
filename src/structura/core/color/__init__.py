"""Colour handling: legacy-exact QColor semantics, HSV (Structure Synth), sRGB <-> linear."""

from .hsv import hsv_to_rgb
from .qcolor_compat import Rgba16, hsv_ints, parse_color
from .srgb import linear_to_srgb, srgb_to_linear, srgb_to_linear_16

__all__ = ["Rgba16", "hsv_ints", "hsv_to_rgb", "linear_to_srgb", "parse_color", "srgb_to_linear", "srgb_to_linear_16"]
