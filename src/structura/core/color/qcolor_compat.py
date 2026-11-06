"""Colour parsing and HSV quantisation with the observable semantics of Qt 5's QColor.

Structure Synth 1.5 routes every absolute colour through QColor, so names, hex forms and the integer
HSV quantisation (hue in whole degrees, -1 when achromatic; saturation/value/alpha in 0..255) are part of
the EisenScript behaviour (docs/06-language-engine.md §8). Implemented from that behavioural description;
verified against PySide6 and the golden corpus in tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .names import NAMED_COLORS

MAX16 = 65535
ACHROMATIC = MAX16


@dataclass(frozen=True, slots=True)
class Rgba16:
    """A colour with 16-bit channels (QColor's internal precision)."""

    r: int
    g: int
    b: int
    a: int = MAX16

    @classmethod
    def from8(cls, r: int, g: int, b: int, a: int = 255) -> Rgba16:
        return cls(r * 257, g * 257, b * 257, a * 257)


def _hex_channels(digits: str, width: int) -> list[int]:
    return [int(digits[i : i + width], 16) for i in range(0, len(digits), width)]


def _hex3(body: str) -> Rgba16:
    r, g, b = (v * 17 for v in _hex_channels(body, 1))
    return Rgba16.from8(r, g, b)


def _hex8(body: str) -> Rgba16:
    a, r, g, b = _hex_channels(body, 2)
    return Rgba16.from8(r, g, b, a)


def _hex9(body: str) -> Rgba16:
    r, g, b = ((v << 4) | (v >> 8) for v in _hex_channels(body, 3))
    return Rgba16(r, g, b)


def _hex6(body: str) -> Rgba16:
    r, g, b = _hex_channels(body, 2)
    return Rgba16.from8(r, g, b)


def _hex12(body: str) -> Rgba16:
    r, g, b = _hex_channels(body, 4)
    return Rgba16(r, g, b)


_HEX_FORMS: dict[int, Callable[[str], Rgba16]] = {3: _hex3, 6: _hex6, 8: _hex8, 9: _hex9, 12: _hex12}


def _parse_hex(body: str) -> Rgba16 | None:
    if any(ch not in "0123456789abcdefABCDEF" for ch in body) or len(body) not in _HEX_FORMS:
        return None
    return _HEX_FORMS[len(body)](body)


def parse_color(text: str) -> Rgba16 | None:
    """Parse a colour like QColor(name): '#rgb', '#rrggbb', '#aarrggbb', '#rrrgggbbb', '#rrrrggggbbbb',
    an SVG colour name (case-insensitive, spaces ignored) or 'transparent'. Returns None if invalid."""
    if not text:
        return None
    if text.startswith("#"):
        return _parse_hex(text[1:])
    key = text.replace(" ", "").lower()
    if key == "transparent":
        return Rgba16(0, 0, 0, 0)
    rgb = NAMED_COLORS.get(key)
    return Rgba16.from8(*rgb) if rgb else None


def _qround(x: float) -> int:
    return int(x + 0.5) if x >= 0 else int(x - 0.5)


def _fuzzy_equal(p: float, q: float) -> bool:
    return abs(p - q) * 1e12 <= min(abs(p), abs(q))


def _raw_hsv(c: Rgba16) -> tuple[int, int, int]:
    """QColor::toHsv internals: (hue*100 or ACHROMATIC, saturation16, value16)."""
    r, g, b = c.r / MAX16, c.g / MAX16, c.b / MAX16
    mx, mn = max(r, g, b), min(r, g, b)
    delta = mx - mn
    value = _qround(mx * MAX16)
    if abs(delta) <= 1e-12:
        return ACHROMATIC, 0, value
    sat = _qround(delta / mx * MAX16)
    if _fuzzy_equal(r, mx):
        hue = (g - b) / delta
    elif _fuzzy_equal(g, mx):
        hue = 2.0 + (b - r) / delta
    else:
        hue = 4.0 + (r - g) / delta
    hue *= 60.0
    if hue < 0.0:
        hue += 360.0
    return _qround(hue * 100.0), sat, value


def div257(x: int) -> int:
    """Rounded 16-bit → 8-bit channel reduction (round(x / 257))."""
    return (x - (x >> 8) + 0x80) >> 8


def hsv_ints(c: Rgba16) -> tuple[int, int, int, int]:
    """(hue, saturation, value, alpha) as QColor's hue()/saturation()/value()/alpha() return them."""
    hue100, sat, val = _raw_hsv(c)
    hue = -1 if hue100 == ACHROMATIC else hue100 // 100
    return hue, div257(sat), div257(val), div257(c.a)


def _near(p: np.ndarray, mx: np.ndarray) -> np.ndarray:
    result: np.ndarray = np.abs(p - mx) * 1e12 <= np.minimum(np.abs(p), np.abs(mx))
    return result


def _div257_array(x: np.ndarray) -> np.ndarray:
    result: np.ndarray = (x - (x >> 8) + 0x80) >> 8
    return result


def hsv_ints_array(rgb8: np.ndarray) -> np.ndarray:
    """Vectorised hsv_ints for an (N, 3) array of 8-bit RGB (alpha 255). Same arithmetic as _raw_hsv."""
    c = rgb8.astype(np.int64) * 257 / MAX16
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    mx, mn = c.max(axis=1), c.min(axis=1)
    delta = mx - mn
    value = np.floor(mx * MAX16 + 0.5).astype(np.int64)
    achromatic = np.abs(delta) <= 1e-12
    safe = np.where(achromatic, 1.0, delta)
    sat = np.where(achromatic, 0, np.floor(safe / np.where(mx == 0, 1.0, mx) * MAX16 + 0.5)).astype(np.int64)
    other = np.where(_near(g, mx), 2.0 + (b - r) / safe, 4.0 + (r - g) / safe)
    hue = np.where(_near(r, mx), (g - b) / safe, other) * 60.0
    hue = np.where(hue < 0.0, hue + 360.0, hue)
    hue100 = np.floor(hue * 100.0 + 0.5).astype(np.int64)
    hue_out = np.where(achromatic, -1, hue100 // 100)
    return np.stack([hue_out, _div257_array(sat), _div257_array(value)], axis=1).astype(np.int32)
