"""Perceptual colour maths on display colours: hex ↔ sRGB ↔ OKLab/OKLCH, mixing, WCAG contrast.

Used by the theme derivation rules (docs/13 §4) and the brand generator. Scalar and dependency-free.
"""

from __future__ import annotations

import math

RGB = tuple[float, float, float]


def hex_to_rgb(value: str) -> RGB:
    """'#rgb', '#rrggbb' or '#rrggbbaa' (alpha ignored) → sRGB floats in [0, 1]."""
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return (int(v[0:2], 16) / 255, int(v[2:4], 16) / 255, int(v[4:6], 16) / 255)


def rgb_to_hex(rgb: RGB) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * math.copysign(abs(c) ** (1 / 2.4), c) - 0.055


def rgb_to_oklab(rgb: RGB) -> RGB:
    r, g, b = (_to_linear(c) for c in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_rgb(lab: RGB) -> RGB:
    big_l, a, b = lab
    l_ = (big_l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (big_l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (big_l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return (_to_srgb(r), _to_srgb(g), _to_srgb(bb))


def oklch(value: str) -> RGB:
    """Hex → (L, C, h in degrees)."""
    big_l, a, b = rgb_to_oklab(hex_to_rgb(value))
    return (big_l, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def from_oklch(big_l: float, c: float, h: float) -> str:
    """(L, C, h) → hex, reducing chroma until the colour fits the sRGB gamut."""
    for _ in range(40):
        rgb = oklab_to_rgb((big_l, c * math.cos(math.radians(h)), c * math.sin(math.radians(h))))
        if all(-1e-4 <= v <= 1 + 1e-4 for v in rgb):
            return rgb_to_hex(rgb)
        c *= 0.9
    return rgb_to_hex(oklab_to_rgb((big_l, 0.0, 0.0)))


def mix(c1: str, c2: str, t: float) -> str:
    """Perceptual mix of two hex colours (t = 0 → c1, t = 1 → c2)."""
    a, b = rgb_to_oklab(hex_to_rgb(c1)), rgb_to_oklab(hex_to_rgb(c2))
    lab = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
    return rgb_to_hex(oklab_to_rgb(lab))


def gradient(stops: list[str], t: float) -> str:
    """Sample a multi-stop gradient at t in [0, 1]."""
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mix(stops[i], stops[i + 1], t - i)


def relative_luminance(value: str) -> float:
    r, g, b = (_to_linear(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.x contrast ratio (1 … 21)."""
    a, b = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
